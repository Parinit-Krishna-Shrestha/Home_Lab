# 🏠 Home Lab — Personal Cloud Infrastructure Platform

> A continuously operated, multi-site infrastructure platform built on Proxmox VE, featuring containerized services, automated offsite disaster recovery, and mesh VPN connectivity.

> 継続的に運用中のマルチサイト・インフラ基盤。Proxmox VE 上のコンテナ化されたサービス群、自動オフサイト災害復旧、メッシュ VPN 接続を特徴とします。

---

## Table of Contents / 目次

- [Overview / 概要](#overview--概要)
- [Topology / トポロジー](#topology--トポロジー)
- [Features / 機能一覧](#features--機能一覧)
- [Repository Structure / リポジトリ構成](#repository-structure--リポジトリ構成)
- [Technologies / 使用技術](#technologies--使用技術)
- [Documentation / ドキュメント](#documentation--ドキュメント)
- [Background / 背景](#background--背景)
- [Roadmap / ロードマップ](#roadmap--ロードマップ)

---

## Overview / 概要

This repository documents the design, configuration, and operational tooling for my personal cloud infrastructure platform — a system I operate continuously as a practical learning environment for enterprise-grade infrastructure engineering.

本リポジトリは、個人のクラウドインフラ基盤の設計・構成・運用ツールをまとめたものです。エンタープライズ水準のインフラエンジニアリングを実践的に学ぶ場として、継続的に運用しています。

The platform consists of two geographically separated nodes connected over a Tailscale WireGuard mesh:

この基盤は、Tailscale WireGuard メッシュで接続された、地理的に離れた 2 つのノードで構成されます。

| Site | Location | Role | Hardware |
|------|----------|------|----------|
| **Primary** | Japan 🇯🇵 | Proxmox VE hypervisor with LXC container fleet | Intel i5-6300U, 8 GB RAM, 477 GB SSD |
| **DR Site** | Nepal 🇳🇵 | Offsite backup & edge services (Pi-hole) | Raspberry Pi (aarch64), 1.9 TB external SSD |

---

## Topology / トポロジー

<p align="center">
  <img src="images/Topology.png" alt="Platform Topology" width="700">
</p>

---

## Features / 機能一覧

### Infrastructure Services / インフラサービス
- **Containerized Service Isolation** — Each service runs in a dedicated unprivileged LXC container with minimal resource allocation, following the principle of least privilege.
- **Media Streaming** — Jellyfin media server with bind-mounted access to the shared storage pool.
- **Network File Sharing** — Samba standalone server providing guest-accessible SMB shares.
- **VPN Gateway** — Tailscale exit node running as an unprivileged container with TUN/TAP device passthrough.

### Disaster Recovery / 災害復旧
- **Offsite Replication** — Automated `rsync` synchronization of the primary media pool to a geographically remote Raspberry Pi over an encrypted Tailscale tunnel.
- **Scheduled Execution** — Monthly cron job (1st of each month, 02:00 JST) balancing storage write endurance with data freshness.
- **Fault-Tolerant Mounts** — External SSD mounted via `/etc/fstab` with UUID identification and `nofail` for headless boot reliability.

### Monitoring & Automation / 監視と自動化
- **Health Checks** — Python-based monitoring script that uses `pct exec` to verify remote VPN node reachability and local storage capacity without requiring Tailscale on the hypervisor host.
- **Structured Logging** — `PIPESTATUS`-based exit code capture in sync scripts for operational auditing.

---

## Repository Structure / リポジトリ構成

```
Home_Lab/
├── README.md                              # This file
├── docs/
│   ├── architecture.md                    # Platform architecture deep dive
│   └── disaster-recovery.md               # DR strategy & offsite replication
├── configs/
│   ├── proxmox/
│   │   ├── lxc-100-tailscale.conf         # Gateway container definition
│   │   ├── lxc-101-jellyfin.conf          # Media server container definition
│   │   └── lxc-102-samba.conf             # File server container definition
│   └── smb.conf                           # Sanitized Samba configuration
└── scripts/
    ├── healthcheck.py                     # Infrastructure monitoring script
    └── dr_sync.sh                         # Offsite backup synchronization
```

---

## Technologies / 使用技術

| Category | Technology |
|----------|-----------|
| Hypervisor | Proxmox VE 8.4 |
| Containerization | LXC (Unprivileged) |
| Storage | LVM Thin Provisioning, ext4 |
| Networking | Linux Bridge (`vmbr0`), Tailscale (WireGuard) |
| Media | Jellyfin |
| File Sharing | Samba |
| Backup | rsync over SSH/Tailscale |
| DNS | Pi-hole |
| Scheduling | cron |
| Monitoring | Python 3, `pct exec` |
| DR Node OS | Debian 12 (Bookworm) on Raspberry Pi |

---

## Documentation / ドキュメント

Detailed technical documentation is available in both English and Japanese:

技術ドキュメントは日本語・英語の両方で提供しています。

| Document | Description |
|----------|-------------|
| [Architecture](docs/architecture.md) | Proxmox host design, LXC resource allocation, networking, and storage architecture |
| [Disaster Recovery](docs/disaster-recovery.md) | Offsite backup strategy, Tailscale mesh routing, and fault-tolerant storage mounts |

---

## Background / 背景

This platform evolved from my vocational school graduation research (卒業研究), [**Media_File_Server**](https://github.com/Parinit-Krishna-Shrestha/Media_File_Server), where I designed and built a media and file server from scratch — covering hardware selection, Proxmox virtualization, Samba file sharing, Tailscale VPN, and Jellyfin media streaming. That graduation research gave me the foundational knowledge in hypervisor management, container networking, and storage architecture that I continue to build upon here.

この基盤は、専門学校の卒業研究 [**Media_File_Server**](https://github.com/Parinit-Krishna-Shrestha/Media_File_Server) から発展したものです。その卒業研究では、ハードウェア選定から Proxmox 仮想化、Samba ファイル共有、Tailscale VPN、Jellyfin メディアストリーミングに至るまで、メディア＆ファイルサーバーをゼロから設計・構築しました。ハイパーバイザー管理、コンテナネットワーキング、ストレージアーキテクチャの基礎知識は、その卒業研究で学んだものであり、この基盤で引き続き実践・発展させています。

What began as graduation research has since grown into a live, multi-site infrastructure platform with automated disaster recovery — a system I maintain and improve continuously as part of my ongoing effort to deepen my understanding of cloud infrastructure operations.

卒業研究として始まったものが、今では自動災害復旧を備えたマルチサイト・インフラ基盤へと成長しました。クラウドインフラ運用への理解を深めるため、日々メンテナンスと改善を続けています。

I am currently pursuing university studies where my graduation research focuses on **Comparative Performance Analysis of Signature-Based and Machine Learning Behavior-Based Intrusion Detection Systems**. As an extension of this research, I plan to develop a Hybrid IDS that combines both approaches and deploy it on this live infrastructure platform — turning the Home Lab into a testbed for real-world intrusion detection.

現在、大学では**シグネチャベースと機械学習による振る舞いベースの侵入検知システムの比較性能分析**を卒業研究のテーマとして取り組んでいます。この研究の発展として、両方のアプローチを組み合わせたハイブリッド IDS を開発し、この本番インフラ基盤にデプロイする予定です。ホームラボを実環境での侵入検知のテストベッドとして活用することを目指しています。

---

## Roadmap / ロードマップ

There is still much to learn and improve. The following items represent areas I would like to explore next:

まだまだ学ぶべきこと、改善すべきことがたくさんあります。以下は今後取り組みたい項目です。

- [ ] **Hybrid IDS Deployment** — Deploy a hybrid intrusion detection system combining signature-based and ML behavior-based detection, built upon my university graduation research.
- [ ] **Monitoring Stack** — Deploy Prometheus + Grafana for time-series metrics collection and visualization.
- [ ] **Infrastructure as Code** — Migrate container definitions to Terraform or Ansible for reproducible deployments.
- [ ] **Alerting** — Integrate health check results with a notification system (e.g., Slack webhook or email).
- [ ] **Automated Testing** — Add CI/CD pipeline for configuration linting and validation.
- [ ] **High Availability** — Explore Proxmox clustering when additional hardware becomes available.
- [ ] **Backup Verification** — Implement automated restore testing to validate backup integrity.

---

## License

This project is shared for educational and portfolio purposes.

---

<p align="center">
  <i>Built and operated with curiosity. Always learning, always improving.</i><br/>
  <i>好奇心を持って構築・運用。常に学び、常に改善。</i>
</p>
