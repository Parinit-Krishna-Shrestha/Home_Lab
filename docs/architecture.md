# Architecture — Platform Design & Engineering Decisions
# アーキテクチャ — 基盤設計とエンジニアリング上の判断

> This document provides a detailed technical overview of the Home Lab infrastructure platform's architecture, covering the Proxmox hypervisor, LXC container fleet, storage design, and network topology.

> 本ドキュメントでは、ホームラボ・インフラ基盤のアーキテクチャについて、Proxmox ハイパーバイザー、LXC コンテナ群、ストレージ設計、ネットワークトポロジーを含む技術的な詳細を解説します。

---

## Table of Contents / 目次

- [Hypervisor Host / ハイパーバイザーホスト](#hypervisor-host--ハイパーバイザーホスト)
- [Storage Architecture / ストレージアーキテクチャ](#storage-architecture--ストレージアーキテクチャ)
- [Container Fleet / コンテナ群](#container-fleet--コンテナ群)
  - [CT100 — Tailscale Gateway](#ct100--tailscale-gateway)
  - [CT101 — Jellyfin Media Server](#ct101--jellyfin-media-server)
  - [CT102 — Samba File Server](#ct102--samba-file-server)
- [Network Design / ネットワーク設計](#network-design--ネットワーク設計)
- [Monitoring / 監視](#monitoring--監視)
- [Design Principles / 設計方針](#design-principles--設計方針)

---

## Hypervisor Host / ハイパーバイザーホスト

| Specification | Value |
|---------------|-------|
| CPU | Intel Core i5-6300U @ 2.40 GHz (2 cores / 4 threads) |
| Memory | 7.6 GiB DDR4 |
| Storage | 476.9 GB SSD |
| OS | Proxmox VE 8.4.0 |
| Mode | Standalone node (no cluster) |

### Why Proxmox VE / なぜ Proxmox VE か

Proxmox VE was chosen as the hypervisor for several practical reasons:

Proxmox VE をハイパーバイザーとして選択した実用的な理由：

1. **Type-1 Hypervisor** — Running directly on bare metal provides better resource efficiency than a hosted hypervisor. The i5-6300U has limited compute resources, so eliminating a host OS layer is meaningful.

   **Type-1 ハイパーバイザー** — ベアメタル上で直接動作するため、ホスト型ハイパーバイザーよりリソース効率が高い。i5-6300U のコンピュートリソースは限られているため、ホスト OS 層の排除は重要です。

2. **LXC-native support** — Proxmox provides first-class LXC container management through its API and CLI (`pct`), which is more resource-efficient than full VMs for single-purpose services.

   **LXC ネイティブサポート** — Proxmox は API と CLI（`pct`）を通じた LXC コンテナ管理を標準提供しており、単一目的のサービスにはフル VM よりリソース効率が良い。

3. **Web UI for operations** — Proxmox's built-in web interface simplifies routine tasks like container lifecycle management and backup scheduling — important for a platform operated by a single person.

   **運用向け Web UI** — Proxmox 内蔵の Web インターフェースにより、コンテナのライフサイクル管理やバックアップスケジューリングなどの日常業務が簡素化される。一人で運用する基盤にとって重要な要素です。

### Why standalone (no cluster) / なぜスタンドアロン（非クラスタ）か

The platform currently runs as a standalone node because only one physical server is available. Proxmox clustering requires a minimum of three nodes for quorum. This is an honest constraint of the current setup, and exploring clustering is part of the future roadmap as hardware becomes available.

現在、物理サーバーが 1 台しかないため、スタンドアロンノードとして運用しています。Proxmox クラスタリングにはクォーラムのために最低 3 ノードが必要です。これは現在の環境の正直な制約であり、ハードウェアが増えた段階でクラスタリングを検討する予定です。

---

## Storage Architecture / ストレージアーキテクチャ

```
476.9 GB SSD
├── Proxmox VE Root
├── LVM Thin Pool (local-lvm)
│   ├── vm-100-disk-0 (7 GB)   → CT100 rootfs
│   ├── vm-101-disk-0 (8 GB)   → CT101 rootfs
│   └── vm-102-disk-0 (58 GB)  → CT102 rootfs
└── /mnt/media-storage (400 GB)
    ├── audio/
    └── video/
```

### LVM Thin Provisioning / LVM シンプロビジョニング

LVM Thin Provisioning is used for the container root filesystems. This approach was chosen because:

コンテナのルートファイルシステムには LVM シンプロビジョニングを使用しています。この選択の理由：

- **Space efficiency** — Thin volumes allocate physical storage on-demand rather than reserving it upfront. On a single 477 GB disk serving multiple containers, this is critical to avoid wasting space.

  **容量効率** — シンボリュームは物理ストレージを事前予約せずオンデマンドで割り当てる。477 GB の単一ディスクで複数のコンテナを稼働させるため、容量の無駄を避けることが重要です。

- **Snapshot support** — Thin provisioning enables efficient copy-on-write snapshots, which are valuable for pre-upgrade backups of container state.

  **スナップショット対応** — シンプロビジョニングにより効率的な CoW スナップショットが可能で、アップグレード前のコンテナ状態バックアップに有用です。

### Media Storage Mount / メディアストレージマウント

The 400 GB `/mnt/media-storage` mount is a dedicated partition on the same physical SSD, separate from the LVM thin pool. Media files (audio, video) are stored here and bind-mounted into the Jellyfin and Samba containers. This design avoids bloating the thin pool with large media files and ensures container root disks remain small and manageable.

400 GB の `/mnt/media-storage` マウントは、LVM シンプールとは別の同一物理 SSD 上の専用パーティションです。メディアファイル（音楽・動画）はここに保存され、Jellyfin と Samba のコンテナにバインドマウントされます。この設計により、大きなメディアファイルでシンプールが肥大化するのを防ぎ、コンテナのルートディスクを小さく管理しやすい状態に維持します。

---

## Container Fleet / コンテナ群

All containers run as **unprivileged LXC containers**. This is a deliberate security decision: unprivileged containers map the container's root user (UID 0) to a high-numbered UID on the host (e.g., 100000), so even if a process escapes the container, it has no meaningful privileges on the host. For a platform that faces the internet through a VPN gateway, this is a baseline security requirement.

すべてのコンテナは**非特権 LXC コンテナ**として実行されます。これは意図的なセキュリティ上の判断です。非特権コンテナはコンテナの root ユーザー（UID 0）をホスト上の高い UID（例：100000）にマッピングするため、プロセスがコンテナから脱出しても、ホスト上で意味のある権限を持ちません。VPN ゲートウェイを通じてインターネットに接する基盤にとって、これはセキュリティの基本要件です。

### CT100 — Tailscale Gateway

**Configuration file**: [`lxc-100-tailscale.conf`](../configs/proxmox/lxc-100-tailscale.conf)

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| `cores` | 1 | VPN routing is not CPU-intensive; 1 core is sufficient. |
| `memory` | 512 MB | Tailscale's `tailscaled` daemon has a small memory footprint. |
| `rootfs` | 7 GB | Minimal OS install + Tailscale binary. |
| `unprivileged` | 1 | Security best practice (see above). |
| `features` | `nesting=1` | Required for Tailscale to create its userspace networking. |
| `onboot` | 1 | Gateway must start automatically — it is the VPN entry point. |

**TUN/TAP Device Passthrough:**

```
lxc.cgroup2.devices.allow: c 10:200 rwm
lxc.mount.entry: /dev/net/tun dev/net/tun none bind,create=file 0 0
```

These two lines are the key to running Tailscale inside an unprivileged LXC container:

この 2 行が、非特権 LXC コンテナ内で Tailscale を実行するための鍵です：

- `c 10:200 rwm` grants the container access to the TUN device (character device, major 10, minor 200) with read/write/mknod permissions through the cgroup2 device controller.
- The bind mount makes `/dev/net/tun` from the host visible inside the container's filesystem.

  `c 10:200 rwm` は cgroup2 デバイスコントローラを通じて TUN デバイス（キャラクタデバイス、メジャー 10、マイナー 200）への読み書き・mknod 権限をコンテナに付与します。バインドマウントにより、ホストの `/dev/net/tun` がコンテナのファイルシステム内で可視化されます。

**Why this matters**: The alternative — running Tailscale on the Proxmox host itself — would expose the hypervisor's network stack to the VPN mesh. By isolating Tailscale in a dedicated unprivileged container, the hypervisor remains unreachable from the Tailscale network. The host can still interact with VPN nodes when needed by using `pct exec 100` to execute commands inside the gateway container (as used in the [healthcheck script](../scripts/healthcheck.py)).

**これが重要な理由**：代替案として Proxmox ホスト自体で Tailscale を実行する方法もありますが、それではハイパーバイザーのネットワークスタックが VPN メッシュに露出します。Tailscale を専用の非特権コンテナに分離することで、ハイパーバイザーは Tailscale ネットワークから到達不能になります。必要に応じて、ホストは `pct exec 100` を使用してゲートウェイコンテナ内でコマンドを実行できます（[ヘルスチェックスクリプト](../scripts/healthcheck.py)で使用）。

---

### CT101 — Jellyfin Media Server

**Configuration file**: [`lxc-101-jellyfin.conf`](../configs/proxmox/lxc-101-jellyfin.conf)

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| `cores` | 3 | Media transcoding benefits from multiple cores. Allocated 3 of 4 available threads. |
| `memory` | 512 MB | Sufficient for software transcoding of personal media libraries. |
| `rootfs` | 8 GB | Jellyfin application + metadata cache. |
| `unprivileged` | 1 | Security best practice. |
| `onboot` | 1 | Media service should be available on boot. |

**Bind Mounts:**

```
mp0: /mnt/media-storage/audio,mp=/mnt/audio
mp1: /mnt/media-storage/video,mp=/mnt/video
```

Media directories are bind-mounted from the host's media storage partition into the container. This means Jellyfin never stores media on its own root disk — it reads directly from the shared pool. This also means the Jellyfin container can be rebuilt or replaced without any risk of data loss.

メディアディレクトリはホストのメディアストレージパーティションからコンテナにバインドマウントされます。つまり、Jellyfin は自身のルートディスクにメディアを保存せず、共有プールから直接読み取ります。これにより、Jellyfin コンテナはデータ損失のリスクなしに再構築・置換可能です。

---

### CT102 — Samba File Server

**Configuration file**: [`lxc-102-samba.conf`](../configs/proxmox/lxc-102-samba.conf)

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| `cores` | 1 | SMB file serving is primarily I/O-bound, not CPU-bound. |
| `memory` | 512 MB | Sufficient for Samba daemon and file operations. |
| `rootfs` | 58 GB | Larger root disk for potential local file staging. |
| `features` | `nesting=1` | Enabled for service management flexibility. |
| `unprivileged` | 1 | Security best practice. |
| `onboot` | 1 | File sharing should be available on boot. |

**Samba Configuration** ([`smb.conf`](../configs/smb.conf)):

The Samba server is configured as `standalone server` with `map to guest = bad user` and `guest ok = yes` on shares. This was a deliberate choice for the home environment: it minimizes friction for devices on the local network (smart TVs, tablets, phones) that need read/write access to media files without managing user credentials.

Samba サーバーは `standalone server` として構成され、`map to guest = bad user` と `guest ok = yes` が共有に設定されています。これはホーム環境での意図的な選択です。ローカルネットワーク上のデバイス（スマート TV、タブレット、スマートフォン）がユーザー資格情報を管理せずにメディアファイルへ読み書きアクセスできるよう、摩擦を最小限にしています。

> **Note / 備考**: Guest access is acceptable here because the Samba service is only accessible on the LAN segment behind `vmbr0`. It is not exposed to the Tailscale mesh or the public internet. If the threat model changes (e.g., exposing Samba to VPN clients), this configuration should be revisited with authentication requirements.

> ゲストアクセスが許容されるのは、Samba サービスが `vmbr0` 背後の LAN セグメントでのみアクセス可能であるためです。Tailscale メッシュやパブリックインターネットには公開されていません。脅威モデルが変わった場合（例：Samba を VPN クライアントに公開）、認証要件を含めて構成を見直す必要があります。

---

## Network Design / ネットワーク設計

### Bridge: `vmbr0`

All three containers connect to the `vmbr0` Linux bridge on the Proxmox host. Each container's virtual Ethernet interface (`veth`) is attached to this bridge, providing:

3 つのコンテナすべてが Proxmox ホスト上の `vmbr0` Linux ブリッジに接続されます。各コンテナの仮想イーサネットインターフェース（`veth`）がこのブリッジに接続され、以下を提供します：

- **Layer 2 connectivity** between containers on the same bridge.
- **DHCP addressing** from the LAN's DHCP server (all containers use `ip=dhcp`).
- **Firewall integration** — All container NICs have `firewall=1` enabled, meaning Proxmox's iptables-based firewall rules are applied at the bridge level.

### Tailscale Mesh VPN

<p align="center">
  <img src="../images/Tailscale%20Mesh%20VPN.png" alt="Tailscale Mesh VPN" width="700">
</p>

Tailscale provides the encrypted overlay network connecting the Japan and Nepal sites. Key architectural decisions:

Tailscale は日本とネパールのサイトを接続する暗号化オーバーレイネットワークを提供します。主要なアーキテクチャ上の決定：

1. **CT100 as exit node** — The gateway container is configured as a Tailscale exit node, allowing remote devices to route their internet traffic through the Japan site when needed.

   **CT100 を Exit Node として使用** — ゲートウェイコンテナは Tailscale Exit Node として構成されており、リモートデバイスが必要に応じて日本サイト経由でインターネットトラフィックをルーティングできます。

2. **Tailscale is NOT installed on the Proxmox host** — This is intentional. The hypervisor should have the smallest possible attack surface. Network connectivity to the VPN mesh is achieved through the CT100 container.

   **Tailscale は Proxmox ホストにインストールしていない** — これは意図的です。ハイパーバイザーは可能な限り小さな攻撃対象面を持つべきです。VPN メッシュへのネットワーク接続は CT100 コンテナを通じて実現します。

---

## Monitoring / 監視

Infrastructure health is monitored by [`healthcheck.py`](../scripts/healthcheck.py), a Python script deployed on the Proxmox host.

インフラの健全性は、Proxmox ホストにデプロイされた Python スクリプト [`healthcheck.py`](../scripts/healthcheck.py) で監視しています。

### How it works / 仕組み

The script uses a technique worth noting: it pings VPN nodes through the CT100 gateway container using `pct exec`:

このスクリプトは注目すべき手法を使用しています。`pct exec` を使って CT100 ゲートウェイコンテナを経由して VPN ノードに ping を送信します：

```python
subprocess.run(["pct", "exec", "100", "--", "ping", "-c", "1", "-W", "2", ip])
```

This approach avoids installing Tailscale on the Proxmox host while still allowing the host to verify that remote nodes are reachable on the mesh. `pct exec` runs commands inside the specified container as if from its namespace — so the ping travels through CT100's Tailscale interface.

この方法により、Proxmox ホストに Tailscale をインストールせずに、リモートノードがメッシュ上で到達可能であることを確認できます。`pct exec` は指定されたコンテナの名前空間内でコマンドを実行するため、ping は CT100 の Tailscale インターフェースを経由します。

The script also monitors local storage capacity using `shutil.disk_usage()` to detect if the media pool is approaching capacity.

スクリプトは `shutil.disk_usage()` を使用してローカルストレージ容量も監視し、メディアプールが容量に近づいているかを検出します。

---

## Design Principles / 設計方針

The following principles guide the architecture decisions in this platform. These are not abstract ideals — they are practical responses to the constraints of operating a home infrastructure on limited hardware:

以下の原則がこの基盤のアーキテクチャ上の判断を導いています。これらは抽象的な理想ではなく、限られたハードウェアでホームインフラを運用する制約への実用的な対応です：

1. **Isolation over convenience** — Each service runs in its own container. Rebuilding one service does not affect others.

   **利便性より分離** — 各サービスは専用のコンテナで実行。一つのサービスの再構築が他に影響しない。

2. **Minimal privilege** — All containers are unprivileged. The hypervisor does not participate in the VPN mesh.

   **最小権限** — すべてのコンテナは非特権。ハイパーバイザーは VPN メッシュに参加しない。

3. **Data and compute separation** — Media files live on a shared mount, not inside containers. Containers are disposable; data is not.

   **データとコンピュートの分離** — メディアファイルはコンテナ内ではなく共有マウントに保存。コンテナは使い捨て可能、データはそうではない。

4. **Honest resource allocation** — Each container receives only the resources it needs. A VPN router does not need 3 CPU cores. A media server does.

   **正直なリソース割り当て** — 各コンテナは必要なリソースのみ受け取る。VPN ルーターに 3 CPU コアは不要。メディアサーバーには必要。

---

*For disaster recovery design and offsite replication, see [Disaster Recovery](disaster-recovery.md).*

*災害復旧設計とオフサイト・レプリケーションについては、[災害復旧](disaster-recovery.md)を参照してください。*
