# Server Management

HTTP server は REST API と MCP streamable HTTP を同じ process で起動します。

```text
http://<BRAIN_HOST>:<BRAIN_PORT>/api
http://<BRAIN_HOST>:<BRAIN_PORT>/mcp
```

既定値は `127.0.0.1:15200` です。

## 開発時

全 OS 共通で foreground 起動します。デバッグや一時起動ではこれを使います。

```bash
mise run serve
```

停止は起動中の terminal で `Ctrl-C` です。
`BRAIN_API_TOKEN` や `BRAIN_PORT` を変えた場合は、起動中の `serve` を止めて再実行します。

## 普段使う常駐 task

常駐運用では、通常は OS 別 task を直接呼ばず、以下の wrapper task だけを使います。

| task              | 用途                     |
| ----------------- | ------------------------ |
| `serve-install`   | 常駐 service として登録  |
| `serve-restart`   | 常駐 service を再起動    |
| `serve-status`    | service と health を確認 |
| `serve-logs`      | service log を表示       |
| `serve-uninstall` | 常駐 service 登録を削除  |

```bash
mise run serve-install
mise run serve-restart
mise run serve-status
mise run serve-logs
mise run serve-uninstall
```

wrapper は実行時に OS を判定します。

| OS    | wrapper の内部処理       |
| ----- | ------------------------ |
| macOS | `serve-launchd-*` を実行 |
| Linux | `serve-systemd-*` を実行 |

## macOS

macOS では user の `launchd` service として登録します。
登録先は `~/Library/LaunchAgents/local.<repo-name>.plist` です。

```bash
mise run serve-install
mise run serve-status
mise run serve-logs
mise run serve-restart
```

削除:

```bash
mise run serve-uninstall
```

内部では以下の task が使われます。通常は直接実行しません。

```bash
mise run serve-launchd-install
mise run serve-launchd-status
mise run serve-launchd-logs
mise run serve-launchd-restart
mise run serve-launchd-uninstall
```

## Linux / WSL

Linux では user の `systemd --user` service として登録します。
登録先は `~/.config/systemd/user/local.<repo-name>.service` です。
root 権限は不要です。

```bash
mise run serve-install
mise run serve-status
mise run serve-logs
mise run serve-restart
```

削除:

```bash
mise run serve-uninstall
```

内部では以下の task が使われます。通常は直接実行しません。

```bash
mise run serve-systemd-install
mise run serve-systemd-status
mise run serve-systemd-logs
mise run serve-systemd-restart
mise run serve-systemd-uninstall
```

WSL で `systemd --user` に接続できない場合は、`/etc/wsl.conf` に以下を設定して WSL を再起動します。

```ini
[boot]
systemd=true
```

## VPS / root 管理の Linux service

VPS で system-wide service として登録する場合は、`mise run serve-install` ではなく
既存の deploy script を使います。

```bash
sudo ./deploy/setup.sh /opt/brain
sudo systemctl start brain
sudo systemctl status brain
sudo systemctl restart brain
```

複数 instance を同じ host に置く場合は、`SERVICE_NAME` と `.env` の `BRAIN_PORT` を分けます。

```bash
sudo SERVICE_NAME=brain-project-a ./deploy/setup.sh /opt/brain-project-a
sudo systemctl restart brain-project-a
```

## 複数 instance

同じ PC に複数の brain instance を置く場合は、instance ごとに `.env` の `BRAIN_PORT` を変えます。

```dotenv
BRAIN_HOST=127.0.0.1
BRAIN_PORT=15201
```

`serve-status` は `.env` の `BRAIN_PORT` を簡易的に読み、`/api/health` を確認します。
