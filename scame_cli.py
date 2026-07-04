#!/usr/bin/env python3
"""SCAME-CLI v0 — 授权 agent / 命令行访问选型工具数据的第一块砖。

数据源 = 线上选型工具静态站:
  公开层  data/sample_products_for_rag.jsonl (技术参数,免鉴权)
  授权层  data/prices.enc / data/stock.enc  (AES-256-GCM,口令解密)

授权码来源(优先级):--password 参数 > 环境变量 SCAME_DATA_PASSWORD > ~/.scame-cli.json 的 password 字段
(Phase 1.5 起每人一个授权码,像 API key:有码可查面价/库存,没码只能用公开层)

用法:
  python3 scame_cli.py search 63A 3P+N+E IP67          # 公开层参数搜索
  python3 scame_cli.py info 213.1630                   # 单型号技术参数
  python3 scame_cli.py price 213.1630 [--json]         # 面价(需口令)
  python3 scame_cli.py stock 213.1630 [--json]         # 库存(需口令)
  python3 scame_cli.py quote 213.1630x10 423.6367x5    # 简易报价(需口令)

给 agent:全部子命令支持 --json,输出机器可读 JSON。
加密参数与前端 vault.ts / scripts/encrypt-data.mjs 严格一致:
PBKDF2-SHA256(salt/iter 在密文 envelope 里) → AES-256-GCM,ct=密文+tag。
"""

import argparse
import base64
import hashlib
import json
import os
import sys
import urllib.request
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

DEFAULT_BASE = "https://scame-selection-tool.shaocongzeming.com/"
CONFIG_PATH = Path.home() / ".scame-cli.json"


def load_config() -> dict:
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text("utf-8"))
        except Exception:
            return {}
    return {}


def http_get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "scame-cli/0.1"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


def fetch_products(base: str) -> list[dict]:
    raw = http_get(base + "data/sample_products_for_rag.jsonl").decode("utf-8")
    return [json.loads(line) for line in raw.splitlines() if line.strip()]


def unwrap_master_key(base: str, code: str) -> bytes:
    """用授权码从 keyring.json 解开总钥匙(逐条尝试,像 API key 校验)。"""
    keyring = json.loads(http_get(base + "data/keyring.json"))
    for entry in keyring.get("entries", []):
        wrapping = hashlib.pbkdf2_hmac(
            "sha256", code.encode("utf-8"), base64.b64decode(entry["salt"]), int(keyring["iter"]), dklen=32
        )
        try:
            return AESGCM(wrapping).decrypt(
                base64.b64decode(entry["iv"]), base64.b64decode(entry["wrap"]), None
            )
        except Exception:
            continue
    print("授权码不正确(或已被停用),请联系管理员", file=sys.stderr)
    sys.exit(3)


def decrypt_envelope(raw: bytes, master_key: bytes) -> object:
    env = json.loads(raw)
    try:
        plain = AESGCM(master_key).decrypt(base64.b64decode(env["iv"]), base64.b64decode(env["ct"]), None)
    except Exception:
        print("解密失败:数据已换钥匙,请更新授权码或稍后重试", file=sys.stderr)
        sys.exit(3)
    return json.loads(plain)


def get_password(args) -> str:
    pw = getattr(args, "password", None) or os.environ.get("SCAME_DATA_PASSWORD") or load_config().get("password")
    if not pw:
        print("需要口令:--password / 环境变量 SCAME_DATA_PASSWORD / ~/.scame-cli.json {\"password\": \"...\"}", file=sys.stderr)
        sys.exit(2)
    return pw.strip()


def fetch_prices(base: str, password: str) -> dict[str, dict]:
    data = decrypt_envelope(http_get(base + "data/prices.enc"), unwrap_master_key(base, password))
    return {r["product_code"].strip().upper(): r for r in data}


def fetch_stock(base: str, password: str) -> dict[str, dict]:
    data = decrypt_envelope(http_get(base + "data/stock.enc"), unwrap_master_key(base, password))
    out: dict[str, dict] = {}
    for r in data:
        code = r["product_code"].strip().upper()
        # 同型号多仓取结存量大的
        if code not in out or (r.get("balance_quantity") or 0) > (out[code].get("balance_quantity") or 0):
            out[code] = r
    return out


def norm(code: str) -> str:
    return code.strip().upper()


def emit(obj, as_json: bool, human: str = ""):
    if as_json:
        print(json.dumps(obj, ensure_ascii=False, indent=2))
    else:
        print(human or json.dumps(obj, ensure_ascii=False, indent=2))


def cmd_search(args):
    products = fetch_products(args.base)
    terms = [t.upper() for t in args.terms]
    hits = []
    for p in products:
        s = p.get("structured", {})
        haystack = " ".join(
            str(v) for v in [p.get("product_code"), s.get("产品描述"), s.get("产品大类"), s.get("电流"), s.get("极数_标准化"), s.get("防护等级"), s.get("电压"), s.get("系列")]
        ).upper()
        if all(t in haystack for t in terms):
            hits.append({
                "product_code": p.get("product_code"),
                "描述": s.get("产品描述"),
                "大类": s.get("产品大类"),
                "电流": s.get("电流"),
                "极数": s.get("极数_标准化"),
                "IP": s.get("防护等级"),
                "电压": s.get("电压"),
            })
    hits = hits[: args.limit]
    if args.json:
        emit({"count": len(hits), "results": hits}, True)
    else:
        for h in hits:
            print(f"{h['product_code']:<18} {h['大类'] or '-':<8} {h['电流'] or '-':<6} {h['极数'] or '-':<8} {h['IP'] or '-':<12} {h['描述'] or ''}")
        print(f"-- {len(hits)} 条(limit {args.limit})")


def cmd_info(args):
    products = fetch_products(args.base)
    code = norm(args.code)
    for p in products:
        if norm(p.get("product_code", "")) == code:
            emit(p.get("structured", {}), args.json)
            return
    print(f"查无此型号:{args.code}", file=sys.stderr)
    sys.exit(1)


def cmd_price(args):
    prices = fetch_prices(args.base, get_password(args))
    rec = prices.get(norm(args.code))
    if not rec:
        print(f"面价表无此型号:{args.code}", file=sys.stderr)
        sys.exit(1)
    emit(rec, args.json, f"{rec['product_code']}  面价 ¥{rec['面价_pcs']}  起订 {rec.get('最小起订量', '-')}  {rec.get('产品描述', '')}")


def cmd_stock(args):
    stock = fetch_stock(args.base, get_password(args))
    rec = stock.get(norm(args.code))
    if not rec:
        emit({"product_code": args.code, "found": False}, args.json, f"{args.code}  无库存记录")
        return
    emit(rec, args.json, f"{rec['product_code']}  可用 {rec.get('available_quantity', 0)}  结存 {rec.get('balance_quantity', 0)}  待发货 {rec.get('pending_delivery_quantity', 0)}")


def cmd_quote(args):
    pw = get_password(args)
    prices = fetch_prices(args.base, pw)
    stock = fetch_stock(args.base, pw)
    lines, total = [], 0.0
    for item in args.items:
        if "x" not in item:
            print(f"跳过非法行项(应为 型号x数量):{item}", file=sys.stderr)
            continue
        code_raw, qty_raw = item.rsplit("x", 1)
        code, qty = norm(code_raw), int(qty_raw)
        rec = prices.get(code)
        if not rec:
            lines.append({"product_code": code, "quantity": qty, "error": "面价表无此型号"})
            continue
        subtotal = round(rec["面价_pcs"] * qty, 2)
        total += subtotal
        st = stock.get(code, {})
        lines.append({
            "product_code": code,
            "描述": rec.get("产品描述", ""),
            "面价": rec["面价_pcs"],
            "quantity": qty,
            "小计": subtotal,
            "可用库存": st.get("available_quantity", 0),
        })
    result = {"lines": lines, "合计面价": round(total, 2), "说明": "面价合计,未含折扣;折扣口径以韶聪审批为准"}
    if args.json:
        emit(result, True)
    else:
        for l in lines:
            if "error" in l:
                print(f"{l['product_code']:<18} x{l['quantity']:<5} ⚠ {l['error']}")
            else:
                print(f"{l['product_code']:<18} x{l['quantity']:<5} ¥{l['面价']:<10} 小计 ¥{l['小计']:<12} 库存可用 {l['可用库存']}")
        print(f"合计面价 ¥{result['合计面价']}(未含折扣)")


def main():
    # 公共参数做成 parent,让 --json/--base/--password 写在子命令前后都行(agent 友好)。
    # 默认值必须用 SUPPRESS:父子解析器重复定义同名参数时,子命令的 default 会把
    # 主解析器已解析的值覆盖掉(argparse 已知坑,实测把 --base 覆盖回线上地址)。
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--base", default=argparse.SUPPRESS, help="站点根 URL")
    common.add_argument("--password", default=argparse.SUPPRESS, help="授权码(建议用环境变量或 ~/.scame-cli.json)")
    common.add_argument("--json", action="store_true", default=argparse.SUPPRESS, help="输出 JSON(给 agent)")

    parser = argparse.ArgumentParser(prog="scame-cli", description="SCAME 选型工具数据 CLI(v0)", parents=[common])
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("search", help="公开层参数搜索", parents=[common]);  p.add_argument("terms", nargs="+"); p.add_argument("--limit", type=int, default=20); p.set_defaults(func=cmd_search)
    p = sub.add_parser("info", help="单型号技术参数", parents=[common]);    p.add_argument("code"); p.set_defaults(func=cmd_info)
    p = sub.add_parser("price", help="查面价(需口令)", parents=[common]);  p.add_argument("code"); p.set_defaults(func=cmd_price)
    p = sub.add_parser("stock", help="查库存(需口令)", parents=[common]);  p.add_argument("code"); p.set_defaults(func=cmd_stock)
    p = sub.add_parser("quote", help="简易报价 型号x数量 ...(需口令)", parents=[common]); p.add_argument("items", nargs="+"); p.set_defaults(func=cmd_quote)

    args = parser.parse_args()
    # SUPPRESS 的参数缺省时补默认值
    args.base = getattr(args, "base", None) or load_config().get("base", DEFAULT_BASE)
    if not args.base.endswith("/"):
        args.base += "/"
    args.password = getattr(args, "password", None)
    args.json = getattr(args, "json", False)
    args.func(args)


if __name__ == "__main__":
    main()
