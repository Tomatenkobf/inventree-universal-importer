"""Create an isolated InvenTree database and run this plugin's integration gate.

Run using the virtualenv holding the selected InvenTree tag's requirements and
this plugin. Never reads the deployment's environment configuration or database.
"""

import argparse
import os
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile

parser = argparse.ArgumentParser()
parser.add_argument("--inventree-root", type=Path, required=True)
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
manage = args.inventree_root.resolve() / "src/backend/InvenTree/manage.py"
if not manage.is_file():
    raise SystemExit("Expected a checked-out InvenTree source tree")
base = root / ".test-runs"
base.mkdir(exist_ok=True)
with tempfile.TemporaryDirectory(prefix="isolated-", dir=base) as directory:
    path = Path(directory)
    for name in ("media", "static", "backup"):
        (path / name).mkdir()
    config = path / "config.yaml"
    import yaml

    config.write_text(
        yaml.safe_dump(
            {
                "database": {
                    "ENGINE": "sqlite3",
                    "NAME": str(path / "db.sqlite3"),
                    "wal_mode": False,
                },
                "media_root": str(path / "media"),
                "static_root": str(path / "static"),
                "backup_dir": str(path / "backup"),
                "secret_key": secrets.token_urlsafe(48),
                "plugins_enabled": True,
                "plugin_noinstall": True,
                "site_url": "http://localhost:8000",
                "allowed_hosts": ["testserver", "localhost"],
            }
        )
    )
    env = {k: v for k, v in os.environ.items() if not k.startswith("INVENTREE_")}
    env.update(
        INVENTREE_CONFIG_FILE=str(config),
        INVENTREE_PLUGIN_FILE=str(path / "plugins.txt"),
        INVENTREE_PLUGIN_TESTING_SETUP="true",
        PYTHONPATH=str(root) + os.pathsep + str(manage.parent),
        DJANGO_SETTINGS_MODULE="InvenTree.settings",
    )

    def run(*command):
        subprocess.run([sys.executable, str(manage), *command], env=env, check=True)

    run("migrate", "--noinput")
    # Simulate administrator activation through the ordinary PluginConfig model.
    # Read-only shell startup intentionally does not create missing config rows.
    run(
        "shell",
        "-c",
        "from plugin.models import PluginConfig; from common.settings import set_global_setting; p,_=PluginConfig.objects.get_or_create(key='universal-importer',defaults={'name':'Universal Product Importer'}); p.active=True; p.save(); [set_global_setting(k,True) for k in ('ENABLE_PLUGINS_APP','ENABLE_PLUGINS_URL','ENABLE_PLUGINS_INTERFACE')]",
    )
    run("migrate", "--noinput")
    subprocess.run(
        [
            sys.executable,
            "-c",
            "import django; django.setup(); from plugin.registry import registry; assert registry.get_plugin('universal-importer') is not None; print('NORMAL_STARTUP_OK')",
        ],
        env=env,
        check=True,
    )
    run("check")
    run("collectstatic", "--noinput")
    run(
        "test",
        "tests.integration",
        "--noinput",
        "--testrunner",
        "django.test.runner.DiscoverRunner",
    )
