# Home Lab — Personal Infrastructure Platform

> A two-site infrastructure platform running on Proxmox VE with containerized services, automated offsite backup, and Tailscale mesh VPN connectivity. Running 24/7.

> Proxmox VE 上で稼働する 2 拠点インフラ基盤。コンテナ化されたサービス群、自動オフサイトバックアップ、Tailscale メッシュ VPN 接続。24 時間 365 日運用中。

---

## Table of Contents / 目次

- [Overview / 概要](#overview--概要)
- [Architecture / アーキテクチャ](#architecture--アーキテクチャ)
- [Current Status / 現在の状態](#current-status--現在の状態)
- [What I Built / 構築した内容](#what-i-built--構築した内容)
- [Repository Structure / リポジトリ構成](#repository-structure--リポジトリ構成)
- [Technologies / 使用技術](#technologies--使用技術)
- [Screenshots / スクリーンショット](#screenshots--スクリーンショット)
- [Documentation / ドキュメント](#documentation--ドキュメント)
- [Current Limitations / 現在の制約](#current-limitations--現在の制約)
- [Future Work / 今後の取り組み](#future-work--今後の取り組み)
- [Background / 背景](#background--背景)

---

## Overview / 概要

This repository documents the design, configuration, and operational tooling for my personal infrastructure platform — a system I operate continuously to practice Linux system administration and infrastructure engineering.

本リポジトリは、個人のインフラ基盤の設計・構成・運用ツールをまとめたものです。Linux システム管理とインフラエンジニアリングを実践する場として、継続的に運用しています。

The platform consists of two geographically separated nodes connected over a Tailscale WireGuard mesh:

この基盤は、Tailscale WireGuard メッシュで接続された 2 つのノードで構成されています：

| Site / サイト | Location / 所在地 | Role / 役割 | Hardware / ハードウェア |
|------|----------|------|----------|
| **Primary / メイン** | Japan 🇯🇵 | Proxmox VE hypervisor with LXC containers / LXC コンテナを伴う Proxmox VE ハイパーバイザー | Intel i5-6300U, 8 GB RAM, 477 GB SSD |
| **DR Site / DR サイト** | Nepal 🇳🇵 | Offsite backup & DNS filtering (Pi-hole) / オフサイトバックアップ & DNS フィルタリング (Pi-hole) | Raspberry Pi (aarch64), 1.9 TB external SSD |

---

## Architecture / アーキテクチャ

<p align="center">
  <img src="images/Topology.png" alt="Platform Topology" width="700">
</p>

For a detailed breakdown of the Proxmox host, LXC container configurations, storage design, and networking, see [docs/architecture.md](docs/architecture.md).

Proxmox ホスト、LXC コンテナ構成、ストレージ設計、ネットワーキングの詳細は [docs/architecture.md](docs/architecture.md) を参照してください。

---

## Current Status / 現在の状態

| Item / 項目 | Status / 状態 |
|------|--------|
| Platform / プラットフォーム | **Running 24/7 / 24時間365日稼働中** |
| Primary site / メインサイト | Japan 🇯🇵 |
| DR site / DR サイト | Nepal 🇳🇵 |
| Last major update / 最終更新 | July 2026 / 2026年7月 |

### Currently Hosting / 稼働中のサービス

| Service | Host | Description | 説明 |
|---------|------|-------------|------|
| **Tailscale Exit Node** | CT100 (LXC) | VPN gateway with TUN/TAP passthrough in an unprivileged container | 非特権コンテナ内の TUN/TAP パススルーによる VPN ゲートウェイ |
| **Jellyfin** | CT101 (LXC) | Media streaming server with bind-mounted access to the shared storage pool | 共有ストレージプールへのバインドマウントを持つメディアストリーミングサーバー |
| **Samba** | CT102 (LXC) | SMB file sharing for LAN devices (guest access for home use) | LAN デバイス向け SMB ファイル共有（家庭用ゲストアクセス） |
| **Pi-hole** | Raspberry Pi (Nepal) | Network-wide DNS filtering, running directly on the Pi | Pi 上で直接実行されるネットワーク全体の DNS フィルタリング |

---

## What I Built / 構築した内容

This section describes the engineering work I personally did to build and operate this platform.

このセクションでは、この基盤を構築・運用するために自分で行ったエンジニアリング作業を記載します。

### Infrastructure Design / インフラ設計
- Designed the multi-site network topology connecting Japan and Nepal over Tailscale
  - Tailscale で日本とネパールを接続するマルチサイトネットワークトポロジーの設計
- Selected and configured Proxmox VE as a Type-1 hypervisor on limited hardware (2C/4T, 8 GB RAM)
  - 限られたハードウェア（2C/4T、8 GB RAM）上で Proxmox VE を Type-1 ハイパーバイザーとして選定・構成
- Planned the LXC container fleet with per-service resource allocation (CPU cores, memory, disk)
  - サービスごとのリソース割り当て（CPU コア、メモリ、ディスク）による LXC コンテナ群の計画

### Container & Service Configuration / コンテナ・サービス構成
- Configured TUN/TAP device passthrough (`/dev/net/tun` bind mount + cgroup2 device allowlist) to run Tailscale inside an unprivileged LXC container — keeping the hypervisor off the VPN mesh
  - 非特権 LXC コンテナ内で Tailscale を実行するための TUN/TAP デバイスパススルー（`/dev/net/tun` バインドマウント + cgroup2 デバイスホワイトリスト）を構成 — ハイパーバイザーを VPN メッシュから分離
- Set up Jellyfin with bind-mounted media directories from the host's shared storage partition
  - ホストの共有ストレージパーティションからのバインドマウントによる Jellyfin のセットアップ
- Configured Samba as a standalone file server with guest-accessible shares for home LAN devices
  - ホーム LAN デバイス向けのゲストアクセス可能な共有を持つスタンドアロンファイルサーバーとして Samba を構成
- All containers run unprivileged (UID remapping) as a baseline security practice
  - すべてのコンテナをセキュリティのベースラインとして非特権（UID リマッピング）で実行

### Storage & Backup / ストレージ・バックアップ
- Configured LVM Thin Provisioning for container root disks (on-demand allocation on a single SSD)
  - コンテナルートディスク用の LVM シンプロビジョニング構成（単一 SSD 上のオンデマンド割り当て）
- Set up the 400 GB media storage partition with bind mounts into multiple containers
  - 複数コンテナへのバインドマウントを伴う 400 GB メディアストレージパーティションのセットアップ
- Implemented offsite backup using `rsync` over SSH/Tailscale to the Nepal Raspberry Pi
  - SSH/Tailscale 経由のネパール Raspberry Pi へのオフサイトバックアップの実装
- Configured the Nepal Pi's external SSD mount via `/etc/fstab` with UUID identification and `nofail` for boot-resilient headless operation
  - ブート耐性のあるヘッドレス運用のための UUID 識別と `nofail` による外付け SSD マウント構成
- Wrote the sync script ([`dr_sync.sh`](scripts/dr_sync.sh)) with bandwidth throttling, `PIPESTATUS` error detection, and structured logging
  - 帯域幅制限、`PIPESTATUS` エラー検出、構造化ログを備えた同期スクリプト（[`dr_sync.sh`](scripts/dr_sync.sh)）の作成

### Monitoring / 監視
- Built a health monitoring script ([`healthcheck.py`](scripts/healthcheck.py)) that uses `pct exec` to ping VPN nodes through the gateway container — allowing the Proxmox host to check remote node status without running Tailscale itself
  - `pct exec` を使用してゲートウェイコンテナ経由で VPN ノードに ping を送信するヘルスモニタリングスクリプト（[`healthcheck.py`](scripts/healthcheck.py)）の構築 — Proxmox ホスト自体で Tailscale を実行せずにリモートノードの状態を確認可能

---

## Repository Structure / リポジトリ構成

```
Home_Lab/
├── README.md
├── docs/
│   ├── architecture.md          # Host, containers, storage, networking / ホスト、コンテナ、ストレージ、ネットワーキング
│   └── disaster-recovery.md     # Offsite backup, Tailscale routing, recovery / オフサイトバックアップ、Tailscale ルーティング、復旧
├── configs/
│   ├── proxmox/
│   │   ├── lxc-100-tailscale.conf
│   │   ├── lxc-101-jellyfin.conf
│   │   └── lxc-102-samba.conf
│   └── smb.conf
├── scripts/
│   ├── healthcheck.py
│   └── dr_sync.sh
└── images/
```

---

## Technologies / 使用技術

| Category / カテゴリ | Technology / 技術 |
|----------|-----------|
| Hypervisor / ハイパーバイザー | Proxmox VE 8.4 |
| Containerization / コンテナ化 | LXC (Unprivileged / 非特権) |
| Storage / ストレージ | LVM Thin Provisioning, ext4 |
| Networking / ネットワーキング | Linux Bridge (`vmbr0`), Tailscale (WireGuard) |
| Media / メディア | Jellyfin |
| File Sharing / ファイル共有 | Samba |
| Backup / バックアップ | rsync over SSH/Tailscale |
| DNS | Pi-hole |
| Scheduling / スケジューリング | cron |
| Monitoring / 監視 | Python 3, `pct exec` |
| DR Node OS / DR ノード OS | Debian 12 (Bookworm) on Raspberry Pi |

---

## Screenshots / スクリーンショット

### Proxmox Dashboard / Proxmox ダッシュボード

<p align="center">
  <img src="images/Proxmox%20screenshot.png" alt="Proxmox Dashboard" width="700">
</p>

### LXC Container List / LXC コンテナ一覧 (`pct list`)

<p align="center">
  <img src="images/LXC%20list.png" alt="LXC Container List">
</p>

### Tailscale Status / Tailscale ステータス (`tailscale status`)

<p align="center">
  <img src="images/tailscale%20status.png" alt="Tailscale Status" width="700">
</p>

---

## Documentation / ドキュメント

Detailed technical documentation is available in both English and Japanese:

技術ドキュメントは日本語・英語の両方で提供しています。

| Document / ドキュメント | Description / 説明 |
|----------|-------------|
| [Architecture](docs/architecture.md) | Proxmox host design, LXC resource allocation, networking, and storage / Proxmox ホスト設計、LXC リソース割り当て、ネットワーキング、ストレージ |
| [Disaster Recovery](docs/disaster-recovery.md) | Offsite backup strategy, Tailscale mesh routing, and recovery procedures / オフサイトバックアップ戦略、Tailscale メッシュルーティング、復旧手順 |

---

## Current Limitations / 現在の制約

Being honest about what this platform does not yet have:

この基盤がまだ持っていないものについて正直に記載します：

- **Single Proxmox node** — No high availability or clustering. A hardware failure means downtime until a replacement is provisioned.
  - **単一 Proxmox ノード** — 高可用性やクラスタリングなし。ハードウェア障害が発生すると、代替機が用意されるまでダウンタイムが発生。
- **No monitoring dashboard** — Health checks exist but there is no time-series visualization (Prometheus/Grafana).
  - **監視ダッシュボードなし** — ヘルスチェックはあるが、時系列可視化（Prometheus/Grafana）はなし。
- **No automated alerting** — Sync failures and node outages are logged but do not trigger notifications.
  - **自動アラートなし** — 同期失敗やノード障害はログされるが、通知はトリガーされない。
- **Monthly backup schedule** — RPO of up to 30 days. Acceptable for personal media, but not for critical data.
  - **月次バックアップスケジュール** — 最大 30 日の RPO。個人メディアには許容範囲だが、重要データには不十分。
- **No automated restore testing** — Backups are replicated but not periodically verified for restorability.
  - **自動復元テストなし** — バックアップは複製されるが、復元可能性の定期的な検証はされていない。
- **No backup retention policy** — Currently a simple mirror. No versioned snapshots or incremental history.
  - **バックアップ保持ポリシーなし** — 現在は単純なミラーのみ。バージョン付きスナップショットや増分履歴はなし。

---

## Future Work / 今後の取り組み

There is still a lot to learn and improve. These are the specific areas I want to work on next:

まだまだ学ぶべきこと、改善すべきことがたくさんあります。次に取り組みたい具体的な項目です。

### Security / セキュリティ
- [ ] **Hybrid IDS deployment** — Deploy a hybrid intrusion detection system combining signature-based and ML behavior-based detection on this live platform, built on my university graduation research.
  - **ハイブリッド IDS デプロイ** — 大学の卒業研究に基づき、シグネチャベースと ML 振る舞いベースの検知を組み合わせたハイブリッド侵入検知システムをこのライブ基盤にデプロイ。

### Backup & Storage / バックアップ・ストレージ
- [ ] **Evaluate BorgBackup or Restic** — Replace the current `rsync` mirror with deduplicated, versioned backups for better storage efficiency and retention.
  - **BorgBackup または Restic の評価** — 現在の `rsync` ミラーを重複排除・バージョン管理されたバックアップに置き換え、ストレージ効率と保持を改善。
- [ ] **Incremental backup schedule** — Move from monthly full sync to more frequent incremental transfers.
  - **増分バックアップスケジュール** — 月次フル同期からより頻繁な増分転送への移行。
- [ ] **Automated restore verification** — Periodically restore a subset of files and verify checksums to confirm backup integrity.
  - **自動復元検証** — ファイルのサブセットを定期的に復元し、チェックサムを検証してバックアップの整合性を確認。
- [ ] **SMART monitoring** — Monitor SSD health on both nodes to detect drive degradation before failure.
  - **SMART 監視** — 両ノードの SSD 健全性を監視し、障害前にドライブの劣化を検出。

### Monitoring & Alerting / 監視・アラート
- [ ] **Prometheus + Grafana** — Deploy a monitoring stack for time-series metrics collection and dashboards.
  - **Prometheus + Grafana** — 時系列メトリクス収集とダッシュボード用の監視スタックをデプロイ。
- [ ] **Email or webhook alerts** — Notify on sync failures, node outages, or storage capacity thresholds.
  - **メールまたは Webhook アラート** — 同期失敗、ノード障害、ストレージ容量閾値の通知。

### Infrastructure as Code / IaC
- [ ] **Ansible playbooks** — Automate container provisioning and configuration for reproducible deployments.
  - **Ansible プレイブック** — 再現可能なデプロイのためのコンテナプロビジョニングと構成の自動化。

---

## Background / 背景

This platform evolved from my vocational school graduation research (卒業研究), [**Media_File_Server**](https://github.com/Parinit-Krishna-Shrestha/Media_File_Server), where I designed and built a media and file server from scratch — covering hardware selection, Proxmox virtualization, Samba file sharing, Tailscale VPN, and Jellyfin media streaming. That graduation research gave me the foundational knowledge in hypervisor management, container networking, and storage architecture that I continue to build upon here.

この基盤は、専門学校の卒業研究 [**Media_File_Server**](https://github.com/Parinit-Krishna-Shrestha/Media_File_Server) から発展したものです。その卒業研究では、ハードウェア選定から Proxmox 仮想化、Samba ファイル共有、Tailscale VPN、Jellyfin メディアストリーミングに至るまで、メディア＆ファイルサーバーをゼロから設計・構築しました。ハイパーバイザー管理、コンテナネットワーキング、ストレージアーキテクチャの基礎知識は、その卒業研究で学んだものであり、この基盤で引き続き実践・発展させています。

What began as graduation research has since grown into a live, two-site infrastructure platform with automated offsite backup — a system I maintain and improve as I continue learning.

卒業研究として始まったものが、自動オフサイトバックアップを備えた 2 拠点インフラ基盤へと成長しました。学び続けながら、メンテナンスと改善を続けています。

I am currently studying at university, where my graduation research focuses on **Comparative Performance Analysis of Signature-Based and Machine Learning Behavior-Based Intrusion Detection Systems**. I plan to extend this research by developing a Hybrid IDS and deploying it on this platform.

現在は大学で学んでおり、卒業研究では**シグネチャベースと機械学習による振る舞いベースの侵入検知システムの比較性能分析**に取り組んでいます。この研究を発展させ、ハイブリッド IDS を開発してこの基盤にデプロイする予定です。

---

## License / ライセンス

This project is shared for educational and portfolio purposes.

このプロジェクトは教育およびポートフォリオ目的で公開しています。
