#!/usr/bin/env bash
# Instala a skill e as ferramentas vedit. Idempotente.
#   ./install.sh                  instala em ~/.claude
#   ./install.sh --project DIR    instala em DIR/.claude (vedit em DIR/.claude/bin)
#   ./install.sh --no-venv        não cria a .venv nem roda o setup
#   ./install.sh --uninstall      remove os links criados por este script
set -eu

# Resolve the repo root through symlinks.
src="${BASH_SOURCE[0]}"
while [ -L "$src" ]; do
  d="$(cd -P "$(dirname "$src")" && pwd)"
  src="$(readlink "$src")"
  case "$src" in /*) ;; *) src="$d/$src" ;; esac
done
ROOT="$(cd -P "$(dirname "$src")" && pwd)"

project=""
use_venv=1
uninstall=0
while [ $# -gt 0 ]; do
  case "$1" in
    --project)
      [ $# -ge 2 ] || { echo "Erro: --project precisa de um diretório." >&2; exit 2; }
      project="$2"; shift 2 ;;
    --no-venv) use_venv=0; shift ;;
    --uninstall) uninstall=1; shift ;;
    -h|--help) sed -n '2,7p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "Opção desconhecida: $1 (use --help)" >&2; exit 2 ;;
  esac
done

if [ -n "$project" ]; then
  if [ "$uninstall" -eq 1 ]; then
    # Never create anything while uninstalling.
    if [ ! -d "$project" ]; then
      echo "Nada a remover: $project não existe."
      exit 0
    fi
  else
    mkdir -p "$project"
  fi
  base="$(cd "$project" && pwd)/.claude"
  bin_dir="$base/bin"
else
  base="$HOME/.claude"
  bin_dir="$HOME/.local/bin"
fi

skipped=0

# points_into_repo LINK: succeed if the symlink LINK resolves to a path inside this repo.
points_into_repo() {
  local t d
  t="$(readlink "$1")" || return 1
  case "$t" in /*) ;; *) t="$(dirname "$1")/$t" ;; esac
  d="$(cd -P "$(dirname "$t")" 2>/dev/null && pwd)" || return 1
  case "$d/$(basename "$t")" in
    "$ROOT"/*) return 0 ;;
    *) return 1 ;;
  esac
}

# link SRC DEST: create/refresh a symlink. Only a symlink that already points into this repo is
# replaced; any other symlink, file or directory is left alone (and counted as skipped).
link() {
  if [ -L "$2" ]; then
    if points_into_repo "$2"; then
      rm "$2"
    else
      echo "  pulando $2 (já existe e aponta para $(readlink "$2"), fora deste repositório; remova ou renomeie à mão se quiser substituir)"
      skipped=$((skipped + 1))
      return 0
    fi
  elif [ -e "$2" ]; then
    echo "  pulando $2 (já existe e não é um link deste instalador; mova ou apague à mão se quiser substituir)"
    skipped=$((skipped + 1))
    return 0
  fi
  mkdir -p "$(dirname "$2")"
  ln -s "$1" "$2"
  echo "  $2 -> $1"
}

# unlink_ours DEST: remove DEST only if it is a symlink pointing inside this repo.
unlink_ours() {
  if [ -L "$1" ] && points_into_repo "$1"; then
    rm "$1"
    echo "  removido $1"
  fi
}

if [ "$uninstall" -eq 1 ]; then
  echo "Removendo links de $base e $bin_dir ..."
  if [ -d "$ROOT/skills" ]; then
    for s in "$ROOT"/skills/*/; do
      [ -d "$s" ] && unlink_ours "$base/skills/$(basename "$s")"
    done
  fi
  if [ -d "$ROOT/agents" ]; then
    for a in "$ROOT"/agents/*.md; do
      [ -f "$a" ] && unlink_ours "$base/agents/$(basename "$a")"
    done
  fi
  unlink_ours "$bin_dir/vedit"
  echo "Pronto."
  exit 0
fi

echo "Instalando em $base ..."
if [ -d "$ROOT/skills" ]; then
  for s in "$ROOT"/skills/*/; do
    [ -d "$s" ] && link "${s%/}" "$base/skills/$(basename "$s")"
  done
else
  echo "  (pasta skills/ ainda não existe; pulando)"
fi
if [ -d "$ROOT/agents" ]; then
  for a in "$ROOT"/agents/*.md; do
    [ -f "$a" ] && link "$a" "$base/agents/$(basename "$a")"
  done
else
  echo "  (pasta agents/ ainda não existe; pulando)"
fi
chmod +x "$ROOT/bin/vedit"
link "$ROOT/bin/vedit" "$bin_dir/vedit"

case ":$PATH:" in
  *":$bin_dir:"*) ;;
  *)
    echo "Aviso: $bin_dir não está no PATH. Adicione a linha certa ao arquivo de configuração do seu shell:"
    echo "  bash (~/.bashrc) ou zsh (~/.zshrc):  export PATH=\"$bin_dir:\$PATH\""
    echo "  fish (~/.config/fish/config.fish):   fish_add_path $bin_dir"
    echo "Enquanto isso, chame pelo caminho completo: $bin_dir/vedit"
    ;;
esac

if [ "$use_venv" -eq 1 ]; then
  echo "Preparando o ambiente Python ..."
  "$ROOT/bin/vedit" setup || echo "Aviso: o setup falhou; rode './bin/vedit setup' depois."
fi
echo "Diagnóstico:"
"$ROOT/bin/vedit" doctor || echo "Faltam itens obrigatórios; siga as instruções acima."
if [ "$skipped" -gt 0 ]; then
  echo "Instalação concluída com $skipped item(ns) pulado(s) (veja as linhas 'pulando' acima); nada foi sobrescrito."
  exit 1
fi
echo "Instalação concluída."
