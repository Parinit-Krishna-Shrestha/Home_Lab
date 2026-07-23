# Disaster Recovery — Offsite Replication & Fault-Tolerant Design
# 災害復旧 — オフサイト・レプリケーションとフォールトトレラント設計

> This document describes the disaster recovery (DR) strategy for the Home Lab platform, covering the offsite Raspberry Pi node in Nepal, the Tailscale VPN routing that connects the two sites, and the automated synchronization process.

> 本ドキュメントでは、ホームラボ基盤の災害復旧（DR）戦略について、ネパールのオフサイト Raspberry Pi ノード、2 つのサイトを接続する Tailscale VPN ルーティング、自動同期プロセスを解説します。

---

## Table of Contents / 目次

- [DR Strategy Overview / DR 戦略概要](#dr-strategy-overview--dr-戦略概要)
- [Offsite Node — Nepal / オフサイトノード — ネパール](#offsite-node--nepal--オフサイトノード--ネパール)
- [Storage Mount Design / ストレージマウント設計](#storage-mount-design--ストレージマウント設計)
- [Network Connectivity / ネットワーク接続](#network-connectivity--ネットワーク接続)
- [Automated Sync Process / 自動同期プロセス](#automated-sync-process--自動同期プロセス)
- [Sync Schedule Design / 同期スケジュール設計](#sync-schedule-design--同期スケジュール設計)
- [Error Handling & Logging / エラーハンドリングとログ](#error-handling--logging--エラーハンドリングとログ)
- [Edge Services / エッジサービス](#edge-services--エッジサービス)
- [Known Limitations / 既知の制約](#known-limitations--既知の制約)
- [Recovery Procedures / 復旧手順](#recovery-procedures--復旧手順)

---

## DR Strategy Overview / DR 戦略概要

The disaster recovery strategy is built around a single principle: **geographic separation of data copies**.

災害復旧戦略は一つの原則に基づいています：**データコピーの地理的分離**。

The primary media pool in Japan (`/mnt/media-storage`) is replicated to a Raspberry Pi node in Nepal (`/mnt/backup`) over an encrypted Tailscale WireGuard tunnel. This ensures that a site-level failure in Japan (hardware failure, natural disaster, theft) does not result in total data loss.

日本のプライマリメディアプール（`/mnt/media-storage`）は、暗号化された Tailscale WireGuard トンネルを介してネパールの Raspberry Pi ノード（`/mnt/backup`）にレプリケーションされます。これにより、日本でのサイトレベルの障害（ハードウェア故障、自然災害、盗難）が完全なデータ損失につながらないことを保証します。

<p align="center">
  <img src="../images/DR%20Strategy%20Overview.png" alt="DR Strategy Overview" width="700">
</p>

---

## Offsite Node — Nepal / オフサイトノード — ネパール

| Specification | Value |
|---------------|-------|
| Hardware | Raspberry Pi (aarch64) |
| OS | Debian GNU/Linux 12 (Bookworm) |
| External Storage | 1.9 TB SSD |
| Storage Mount | `/mnt/backup` (static via `/etc/fstab`) |
| Network Services | Tailscale, Pi-hole |
| Power Profile | Low-power ARM SoC — suitable for always-on edge deployment |

### Why Raspberry Pi / なぜ Raspberry Pi か

The Raspberry Pi was chosen for the DR site because:

DR サイトに Raspberry Pi を選択した理由：

1. **Low power consumption** — The Pi draws approximately 5W under load, making it practical to run 24/7 even in locations where electricity costs matter or where power stability may be limited.

   **低消費電力** — Pi は負荷時でも約 5W で動作し、電力コストが重要な場所や電力安定性が限られる場所でも 24 時間 365 日稼働が現実的。

2. **Headless operation** — The Pi runs without a monitor, keyboard, or mouse. All management is performed over SSH through the Tailscale mesh. This makes it feasible to deploy in a remote location where physical access is infrequent.

   **ヘッドレス運用** — Pi はモニター、キーボード、マウスなしで稼働。すべての管理は Tailscale メッシュ経由の SSH で実行。物理アクセスが稀なリモート拠点への配置を実現可能にします。

3. **Cost-effective redundancy** — A Raspberry Pi with an external SSD provides meaningful offsite redundancy at a fraction of the cost of a cloud storage subscription or a second server.

   **費用効率の良い冗長性** — Raspberry Pi と外付け SSD の組み合わせは、クラウドストレージのサブスクリプションや第 2 サーバーのコストのごく一部で、意味のあるオフサイト冗長性を提供します。

---

## Storage Mount Design / ストレージマウント設計

The 1.9 TB external SSD is statically mounted via `/etc/fstab` using a UUID-based entry:

1.9 TB の外付け SSD は、UUID ベースのエントリを使用して `/etc/fstab` 経由で静的にマウントされています：

```
UUID=<device-uuid>  /mnt/backup  ext4  defaults,nofail  0  2
```

### Why UUID instead of device path / なぜデバイスパスではなく UUID か

Device paths like `/dev/sda1` are assigned by the kernel at boot time based on device enumeration order. If the Pi is rebooted with a different USB device connected, or if the kernel enumerates devices in a different order, `/dev/sda1` might point to the wrong device. UUID identification eliminates this ambiguity — the UUID is a property of the filesystem itself, not the device path.

`/dev/sda1` のようなデバイスパスは、デバイス列挙順序に基づいてブート時にカーネルによって割り当てられます。異なる USB デバイスが接続された状態で Pi が再起動された場合、またはカーネルが異なる順序でデバイスを列挙した場合、`/dev/sda1` が誤ったデバイスを指す可能性があります。UUID による識別はこの曖昧さを排除します — UUID はデバイスパスではなくファイルシステム自体のプロパティです。

### Why `nofail` / なぜ `nofail` か

The `nofail` mount option is critical for headless reliability. Without it:

`nofail` マウントオプションはヘッドレス信頼性にとって重要です。これがない場合：

- If the external SSD is disconnected, fails, or is not detected at boot time, the system will **drop into an emergency shell** and wait for manual intervention.
- On a headless Raspberry Pi in a remote location (Nepal), there is no attached monitor or keyboard to interact with the emergency shell.
- The system would remain stuck and unreachable until someone physically connects peripherals.

  外付け SSD が切断された場合、故障した場合、またはブート時に検出されなかった場合、システムは**緊急シェルに移行**し、手動介入を待ちます。リモート拠点（ネパール）のヘッドレス Raspberry Pi では、緊急シェルに接続するモニターやキーボードがありません。誰かが物理的に周辺機器を接続するまで、システムはスタックしたまま到達不能になります。

With `nofail`, the system boots normally even if the mount fails. The Pi comes online, Tailscale connects, and SSH access is restored — allowing remote diagnosis of why the drive failed to mount.

`nofail` があれば、マウントが失敗してもシステムは正常にブートします。Pi がオンラインになり、Tailscale が接続し、SSH アクセスが復旧 — ドライブのマウント失敗の原因をリモートで診断できます。

> **Engineering trade-off / エンジニアリング上のトレードオフ**: The risk of `nofail` is that the backup sync script might run against an empty `/mnt/backup` directory (just a mount point on the root filesystem) if the SSD fails to mount. To mitigate this, `dr_sync.sh` performs a `mountpoint -q` check on both the source and destination mounts before starting the sync, aborting with a logged error if either is not a mounted filesystem.

> `nofail` のリスクは、SSD のマウントに失敗した場合、バックアップ同期スクリプトが空の `/mnt/backup` ディレクトリ（ルートファイルシステム上のマウントポイントのみ）に対して実行される可能性があることです。これを軽減するため、`dr_sync.sh` は同期開始前にソースと宛先の両マウントに対して `mountpoint -q` チェックを実行し、いずれかがマウントされたファイルシステムでない場合はエラーをログして中止します。

---

## Network Connectivity / ネットワーク接続

### Tailscale Mesh VPN

The Japan and Nepal nodes communicate exclusively through a Tailscale WireGuard mesh. This was chosen over traditional VPN solutions (OpenVPN, IPsec) because:

日本とネパールのノードは Tailscale WireGuard メッシュを通じてのみ通信します。従来の VPN ソリューション（OpenVPN、IPsec）ではなくこれを選択した理由：

1. **NAT traversal** — Both the Japan and Nepal sites are behind consumer-grade NAT routers. Tailscale uses DERP relay servers and UDP hole-punching to establish direct WireGuard connections without requiring port forwarding or static IPs.

   **NAT トラバーサル** — 日本とネパールのサイトは共にコンシューマーグレードの NAT ルーター背後にあります。Tailscale は DERP リレーサーバーと UDP ホールパンチングを使用して、ポートフォワーディングや静的 IP を必要とせずに直接 WireGuard 接続を確立します。

2. **Zero-configuration networking** — Tailscale assigns stable IP addresses (100.x.x.x) to each node. Adding a new device to the mesh requires only installing Tailscale and authenticating — no manual key exchange or configuration file editing.

   **ゼロコンフィグレーション・ネットワーキング** — Tailscale は各ノードに安定した IP アドレス（100.x.x.x）を割り当てます。メッシュへの新規デバイス追加は Tailscale のインストールと認証のみで、手動の鍵交換や構成ファイル編集は不要です。

3. **Encrypted by default** — All traffic between nodes is encrypted with WireGuard (ChaCha20-Poly1305). The `rsync` data transfer over SSH over Tailscale benefits from double encryption, though the primary security boundary is the Tailscale tunnel itself.

   **デフォルトで暗号化** — ノード間のすべてのトラフィックは WireGuard（ChaCha20-Poly1305）で暗号化されます。Tailscale 上の SSH 上の `rsync` データ転送は二重暗号化の恩恵を受けますが、主要なセキュリティ境界は Tailscale トンネル自体です。

### Cross-Site Routing

<p align="center">
  <img src="../images/Cross-Site%20Routing.png" alt="Cross-Site Routing" width="700">
</p>

The `rsync` backup script ([`dr_sync.sh`](../scripts/dr_sync.sh)) runs inside the CT100 gateway container, which has direct Tailscale connectivity to the Nepal Pi (`100.104.209.126`). The host's media storage partition is bind-mounted into CT100 as read-only (`ro=1`), giving the script access to the source data without allowing accidental writes from the container.

`rsync` バックアップスクリプト（[`dr_sync.sh`](../scripts/dr_sync.sh)）は CT100 ゲートウェイコンテナ内で実行され、ネパール Pi（`100.104.209.126`）への Tailscale 接続を直接使用します。ホストのメディアストレージパーティションは読み取り専用（`ro=1`）で CT100 にバインドマウントされており、コンテナからの誤った書き込みを防ぎつつ、スクリプトにソースデータへのアクセスを提供します。

---

## Automated Sync Process / 自動同期プロセス

**Script**: [`dr_sync.sh`](../scripts/dr_sync.sh)

The sync script uses `rsync` over SSH to replicate the Japan media pool to the Nepal node:

同期スクリプトは SSH 上の `rsync` を使用して、日本のメディアプールをネパールノードにレプリケーションします：

```bash
rsync -avh --delete \
  --exclude 'lost+found' \
  --exclude '.Trash-*' \
  --bwlimit=2000 \
  -e "ssh -o StrictHostKeyChecking=accept-new" \
  "${SOURCE_DIR}" \
  "${DEST_USER}@${DEST_HOST}:${DEST_DIR}"
```

### Flag-by-Flag Rationale / フラグごとの理由

| Flag | Purpose |
|------|---------|
| `-a` (archive) | Preserves permissions, timestamps, symlinks, and directory structure. Essential for a faithful copy. |
| `-v` (verbose) | Outputs file-level transfer details for logging. |
| `-h` (human-readable) | Formats sizes in KB/MB/GB in log output. |
| `--delete` | Removes files from the destination that no longer exist on the source. Ensures the backup is a true mirror, not an ever-growing accumulation. |
| `--exclude 'lost+found'` | The `lost+found` directory is created by `ext4` filesystem tools (`e2fsck`) and is owned by root. Attempting to sync it causes permission errors on the destination, especially when the destination is a different filesystem. Excluding it avoids unnecessary failures. |
| `--exclude '.Trash-*'` | Prevents replicating desktop trash directories that may exist on the media mount. |
| `--bwlimit=2000` | Throttles transfer speed to approximately 2000 KB/s (~16 Mbps). This is important because the Nepal site likely has limited upstream bandwidth. Saturating the connection would make the Pi unreachable for SSH management during the sync. |
| `-e "ssh -o StrictHostKeyChecking=accept-new"` | Automatically accepts the SSH host key on first connection. This enables the script to run unattended via cron without hanging on a host key confirmation prompt. After the first connection, subsequent connections verify the stored key normally. |

| フラグ | 目的 |
|--------|------|
| `-a`（アーカイブ） | パーミッション、タイムスタンプ、シンボリックリンク、ディレクトリ構造を保持。忠実なコピーに不可欠。 |
| `-v`（詳細） | ログ用にファイルレベルの転送詳細を出力。 |
| `-h`（人が読める形式） | ログ出力のサイズを KB/MB/GB で書式化。 |
| `--delete` | ソースに存在しなくなったファイルを宛先から削除。バックアップが増え続ける蓄積ではなく、真のミラーであることを保証。 |
| `--exclude 'lost+found'` | `lost+found` ディレクトリは `ext4` ファイルシステムツール（`e2fsck`）によって作成され、root が所有。同期しようとすると、特に宛先が異なるファイルシステムの場合にパーミッションエラーが発生。除外により不必要な失敗を回避。 |
| `--exclude '.Trash-*'` | メディアマウントに存在する可能性のあるデスクトップのゴミ箱ディレクトリのレプリケーションを防止。 |
| `--bwlimit=2000` | 転送速度を約 2000 KB/s（約 16 Mbps）に制限。ネパールサイトは上り帯域幅が限られている可能性が高いため重要。接続を飽和させると、同期中に Pi が SSH 管理に到達不能になる。 |
| `-e "ssh -o StrictHostKeyChecking=accept-new"` | 初回接続時に SSH ホストキーを自動的に受け入れ。ホストキー確認プロンプトでハングすることなく、cron 経由で無人実行可能に。初回接続後、以降の接続は保存されたキーを通常通り検証。 |

---

## Sync Schedule Design / 同期スケジュール設計

```
# Cron entry (CT100 gateway container)
0 2 1 * * /root/scripts/dr_sync.sh
```

The sync runs **monthly**, on the **1st of each month at 02:00 JST**.

同期は**毎月**、**毎月 1 日 02:00 JST** に実行されます。

### Why monthly instead of daily / なぜ日次ではなく月次か

This was a considered trade-off between three factors:

これは 3 つの要因を考慮したトレードオフです：

1. **Storage write endurance** — The external SSD at the Nepal site receives the full `--delete` sync on each run. While modern SSDs have good endurance, minimizing unnecessary write cycles extends the drive's useful life — especially for a remote device that cannot be easily replaced.

   **ストレージ書き込み耐久性** — ネパールサイトの外付け SSD は毎回の実行で完全な `--delete` 同期を受けます。現代の SSD は良好な耐久性を持ちますが、不必要な書き込みサイクルを最小限にすることでドライブの有効寿命を延長します — 特に容易に交換できないリモートデバイスにとって。

2. **Bandwidth constraints** — The international link between Japan and Nepal has limited bandwidth. Running daily syncs of a 400 GB media pool would consume significant bandwidth and potentially interfere with normal internet usage at the Nepal site.

   **帯域幅制約** — 日本とネパール間の国際リンクは帯域幅が限られています。400 GB のメディアプールの日次同期は大量の帯域幅を消費し、ネパールサイトでの通常のインターネット使用に干渉する可能性があります。

3. **Data change rate** — The media pool primarily contains audio and video files that are added infrequently. A monthly sync captures changes with acceptable data loss risk for a personal media collection.

   **データ変更率** — メディアプールには主に追加頻度の低い音声・動画ファイルが含まれます。月次同期は、個人のメディアコレクションとして許容可能なデータ損失リスクで変更をキャプチャします。

> **Honest assessment / 正直な評価**: In a production environment, the RPO (Recovery Point Objective) of up to 30 days would be unacceptable for most workloads. For a personal media server, this represents a reasonable trade-off. If the data were more critical (e.g., documents, databases), the schedule would need to be daily or more frequent.

> 本番環境では、最大 30 日の RPO（Recovery Point Objective）はほとんどのワークロードで許容できません。個人のメディアサーバーとしては、合理的なトレードオフです。データがより重要な場合（例：ドキュメント、データベース）、スケジュールは日次またはそれ以上の頻度にする必要があります。

---

## Error Handling & Logging / エラーハンドリングとログ

### PIPESTATUS-Based Exit Code Capture

```bash
rsync -avh --delete ... | tee -a "$LOG_FILE"

if [ ${PIPESTATUS[0]} -eq 0 ]; then
    echo "--- Sync Completed Successfully: $(date) ---" | tee -a "$LOG_FILE"
else
    echo "--- Sync FAILED: $(date) ---" | tee -a "$LOG_FILE"
fi
```

This pattern deserves explanation. When piping `rsync` output to `tee`, the exit code of the pipeline (`$?`) reflects the exit code of `tee` (the last command), **not** `rsync`. If `rsync` fails but `tee` succeeds at writing the error output, `$?` would be 0, masking the failure.

このパターンには説明が必要です。`rsync` の出力を `tee` にパイプする場合、パイプラインの終了コード（`$?`）は `tee`（最後のコマンド）の終了コードを反映し、`rsync` のものでは**ありません**。`rsync` が失敗しても `tee` がエラー出力の書き込みに成功すれば、`$?` は 0 となり、失敗が隠されます。

`PIPESTATUS` is a Bash array that captures the exit code of **each** command in the pipeline. `PIPESTATUS[0]` is `rsync`'s exit code, allowing accurate success/failure detection.

`PIPESTATUS` はパイプラインの**各**コマンドの終了コードをキャプチャする Bash 配列です。`PIPESTATUS[0]` は `rsync` の終了コードであり、正確な成功/失敗検出を可能にします。

All output is appended to `/var/log/dr_sync.log` for operational auditing.

すべての出力は運用監査のために `/var/log/dr_sync.log` に追記されます。

---

## Edge Services / エッジサービス

The Nepal Raspberry Pi also provides edge network services for the local network at that site:

ネパールの Raspberry Pi は、そのサイトのローカルネットワーク向けのエッジネットワークサービスも提供しています：

| Service | Purpose |
|---------|---------|
| **Pi-hole** | DNS sinkhole for network-wide ad blocking. Provides DNS resolution for all devices on the Nepal LAN. |
| **Tailscale** | Mesh VPN connectivity back to the Japan site. |

This makes the Nepal node dual-purpose: it serves as both a DR backup target **and** a functional edge node providing services to its local network. This is a practical way to justify the hardware cost — a device that only stores backups would be difficult to justify compared to a multi-function edge node.

これによりネパールノードは二重目的となります：DR バックアップターゲット**かつ**ローカルネットワークにサービスを提供する機能的なエッジノードです。ハードウェアコストを正当化する実用的な方法です — バックアップのみを保存するデバイスは、多機能エッジノードと比較して正当化が困難です。

---

## Known Limitations / 既知の制約

Being honest about what this setup does *not* do is as important as describing what it does:

このセットアップが何を*しないか*を正直に述べることは、何をするかを述べることと同様に重要です：

1. **No automated restore testing** — Backups are replicated but not automatically tested for restorability. A future improvement would be to periodically restore a subset of files and verify checksums.

   **自動復元テストなし** — バックアップはレプリケーションされますが、復元可能性の自動テストは行われていません。将来の改善として、定期的にファイルのサブセットを復元しチェックサムを検証することが考えられます。

2. ~~**No mount verification before sync**~~ — **Resolved.** The sync script now performs `mountpoint -q` checks on both the source and destination mounts before starting, aborting with a logged error if either is not mounted.

   ~~**同期前のマウント検証なし**~~ — **解決済み。** 同期スクリプトは、開始前にソースと宛先の両マウントに対して `mountpoint -q` チェックを実行し、いずれかがマウントされていない場合はエラーをログして中止するようになりました。

3. **No alerting on sync failure** — Sync failures are logged to a file but do not trigger any notification. The failure would only be discovered when manually checking logs or running the healthcheck script.

   **同期失敗時のアラートなし** — 同期の失敗はファイルにログされますが、通知はトリガーされません。失敗は手動でログを確認するか、ヘルスチェックスクリプトを実行した時にのみ発見されます。

4. **Single copy at DR site** — There is no redundancy at the Nepal site itself. If the external SSD fails, the offsite backup is lost until a replacement drive is provisioned.

   **DR サイトでの単一コピー** — ネパールサイト自体に冗長性はありません。外付け SSD が故障した場合、交換ドライブが用意されるまでオフサイトバックアップは失われます。

---

## Recovery Procedures / 復旧手順

### Scenario: Primary Node Failure (Japan) / シナリオ：プライマリノード障害（日本）

If the Japan Proxmox host fails completely:

日本の Proxmox ホストが完全に障害を起こした場合：

1. **Access the Nepal Pi** via Tailscale SSH (or physical access if Tailscale is unavailable).

   Tailscale SSH 経由でネパール Pi にアクセス（Tailscale が利用不可の場合は物理アクセス）。

2. **Verify backup integrity** at `/mnt/backup/japan_nas_sync/`.

   `/mnt/backup/japan_nas_sync/` でバックアップの整合性を検証。

3. **Provision new hardware** and install Proxmox VE.

   新しいハードウェアを調達し、Proxmox VE をインストール。

4. **Recreate containers** using the configuration files in this repository (`configs/proxmox/lxc-*.conf`).

   このリポジトリの設定ファイル（`configs/proxmox/lxc-*.conf`）を使用してコンテナを再作成。

5. **Restore media data** by running `rsync` in reverse — from the Nepal Pi back to the new Japan host.

   `rsync` を逆方向に実行してメディアデータを復元 — ネパール Pi から新しい日本ホストへ。

```bash
rsync -avh --progress \
  pi@100.104.209.126:/mnt/backup/japan_nas_sync/ \
  /mnt/media-storage/
```

### Estimated Recovery Time / 推定復旧時間

- **Container recreation**: ~30 minutes (using stored configuration files).
- **Data restoration**: Dependent on data volume and international link speed. For the current ~400 GB media pool at ~2 MB/s, approximately **55 hours**.
- **Total RTO**: Approximately **2–3 days**, including hardware procurement.

  **コンテナ再作成**：約 30 分（保存された設定ファイルを使用）。**データ復元**：データ量と国際リンク速度に依存。現在の約 400 GB メディアプールで約 2 MB/s の場合、約 **55 時間**。**合計 RTO**：ハードウェア調達を含め、約 **2〜3 日**。

---

*For the primary site's architecture and container design, see [Architecture](architecture.md).*

*プライマリサイトのアーキテクチャとコンテナ設計については、[アーキテクチャ](architecture.md)を参照してください。*
