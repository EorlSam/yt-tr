#!/usr/bin/env bash
set -euo pipefail

repo_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
install_root="${XDG_DATA_HOME:-$HOME/.local/share}/yt-tr"
bin_dir="${HOME}/.local/bin"

mkdir -p "$install_root" "$bin_dir"
python3 -m venv "$install_root/venv"
"$install_root/venv/bin/python" -m pip install --upgrade pip
"$install_root/venv/bin/python" -m pip install -r "$repo_dir/requirements.txt"
install -m 0644 "$repo_dir/yt-tr.py" "$install_root/yt-tr.py"

cat > "$bin_dir/yt-tr" <<EOF
#!/usr/bin/env bash
set -euo pipefail
exec "$install_root/venv/bin/python" "$install_root/yt-tr.py" "\$@"
EOF
chmod 0755 "$bin_dir/yt-tr"

echo "Installed yt-tr to $bin_dir/yt-tr"
