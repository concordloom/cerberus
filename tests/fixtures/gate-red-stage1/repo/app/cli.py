import argparse
import json


def render(payload, as_json):
    return json.dumps(payload) if as_json else "ok=%s" % (payload["ok"],)


def main(argv=None):
    parser = argparse.ArgumentParser(prog="fixture")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    print(render({"ok": True}, False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
