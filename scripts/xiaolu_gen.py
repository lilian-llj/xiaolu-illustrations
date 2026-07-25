"""
小鹿风格配图参数化生图脚本（火山方舟 ARK 版）
================================
小鹿 IP v1.0 定稿版。STYLE_PROMPT 已锁死小鹿角色与油画棒马卡龙风格。
通过火山方舟 ARK API 调用 doubao-seedream 模型生图。

使用前提：
  1. 注册火山引擎（console.volcengine.com）并完成实名认证
  2. 进入火山方舟（ark.console.volcengine.com），开通 doubao-seedream 模型
  3. 创建 API Key，设置环境变量：set ARK_API_KEY=xxx
  4. 运行本脚本

铁律：
  - 任何出现小鹿的图，必须用官方标准像垫图：
    --ref-image "<skill>/assets/小鹿-标准像-v1.png"
    纯文字裸生角色会漂移（额头白点/尾巴/鹿角变大），已被实测证明。
  - 零三方依赖（仅标准库）。
  - ARK 标准接口多数不支持 seed 复现：靠多生成挑选满意结果。

用法示例：
  PYTHONUTF8=1 python xiaolu_gen.py --topic "穿搭打卡" --structure "前后对比" ^
    --core-idea "打卡前乱、打卡后成体系" ^
    --composition "<CHAR_LOCK前缀>小鹿站在两堆衣服中间，左边乱堆右边整齐" ^
    --elements "乱堆衣服 / 整齐衣架 / 打卡勾" ^
    --labels "打卡前 / 打卡后 / 21天 / 体系" ^
    --ref-image "assets/小鹿-标准像-v1.png"
"""

import argparse
import base64
import json
import mimetypes
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path


def load_ref_image(ref):
    """把参考图转成 ARK 接受的形式：
    - 若是 http/https URL，直接返回原样
    - 若是本地文件，读成 data:image/<type>;base64,<...> 格式
    """
    if ref.startswith("http://") or ref.startswith("https://"):
        return ref
    p = Path(ref)
    if not p.exists():
        print(f"参考图不存在: {ref}")
        sys.exit(1)
    mime, _ = mimetypes.guess_type(str(p))
    if mime not in ("image/png", "image/jpeg"):
        # ARK 只接受 jpeg/png；按后缀兜底
        mime = "image/png" if p.suffix.lower() == ".png" else "image/jpeg"
    b64 = base64.b64encode(p.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{b64}"

ARK_ENDPOINT = "https://ark.cn-beijing.volces.com/api/v3/images/generations"

# 默认模型：Seedream 5.0 Lite，质量好、支持 2K/3K/4K、性价比高。
# 其他可选：doubao-seedream-5-0-pro-260628（最强）/ -4-5-251128 / -4-0-250828
DEFAULT_MODEL = "doubao-seedream-5-0-lite-260128"


# ============================================================
# 固定风格前缀（小鹿 v1.0 定稿：油画棒肌理 + 低饱和马卡龙 + 幼年梅花鹿）
# 修改需同步 references/xiaolu-ip.md 与 references/style-dna.md
# ============================================================
STYLE_PROMPT = """Generate one standalone 16:9 horizontal Chinese article illustration.

Visual DNA:
Oil pastel / crayon hand-drawn illustration with strong visible texture: grainy strokes, paper tooth, waxy pigment buildup, like a real oil-pastel drawing on paper. Low-saturation macaron color palette: soft muted pink, misty lavender purple, cream yellow, light warm brown. Flat coloring only — absolutely no 3D volume shading, no heavy cast shadows, no glossy rendering, no airbrush gradients. Slightly wobbly outlines on body and objects, coloring may slightly overflow edges for a genuine handmade feel, but facial lines stay smooth and clean. Soft milk-tea cream background with lots of empty space. Sparse handwritten Chinese annotations in soft pink, misty purple, cream yellow and light brown. Warm, healing, milky-soft baby-animal atmosphere. No realistic fur rendering, no 3D render, no metallic highlights, no PPT infographic look, no dense explainer, no dark heavy textures, no digital-flat vector sticker look.

Recurring IP character required:
小鹿, a BABY sika deer fawn with an extremely chubby, short, milky-soft baby body: big round head, short stubby body, tiny short limbs — clearly an infant animal, never adult deer proportions. Light warm brown body with a few soft white sika-deer spots on its back and sides. Two tiny short rounded baby antlers, each tied with a soft pink bow at the base. White patches around eyes and muzzle; exactly 3 small white dots on the BRIDGE OF THE NOSE (not the forehead). Eyes are solid black round bean-like dots with no highlights, no white sclera, no glossy reflections. Pink heart-shaped blush on both cheeks. Small black round nose with a tiny curved smile line. Facial lines smooth and clean. Inner ears light pink, outer ears match body color. No tail visible. 小鹿 wears a misty PURPLE nightcap with white hand-drawn stars and a small white pom-pom tip, plus a misty PURPLE pajamas outfit with soft pink lace trim on BOTH the collar and the hem. The pale cream-yellow crescent moon pillow is an OPTIONAL prop, NOT a required element: when 小鹿 needs its hands free to perform the scene's action, omit the moon pillow entirely and let 小鹿 use both hands for the action; only include the moon pillow when it naturally fits and does not block the action. 小鹿 must perform the core conceptual action, not decorate the scene. Make 小鹿 milky, chubby, babyish, earnest and slightly clumsy.

Color use:
Light warm brown for the deer body with soft white sika spots. Muted macaron pink for key emotion/relationship/highlight labels (blush, bows, lace trim, important tags). Misty macaron lavender purple for sleep cap, pajamas, secondary notes, system states. Cream yellow for the crescent moon pillow and main call-to-action or bright spots. All colors low-saturation macaron tones rendered in visible oil-pastel texture; avoid neon, high saturation, or clean digital fills.

Constraints:
One image explains only one core structure. Keep the main subject around 40%-60% of the canvas. Preserve at least 35% blank white space. Use at most 5-8 short handwritten Chinese labels. Do not write a title in the top-left corner. Do not write the structure type on the image. Do not make it a formal diagram, course slide, or dense explainer. Invent a fresh visual metaphor for this specific article. It should be clear but not instructional, warm but not childish, clean but not sterile.
"""


def build_prompt(args):
    """把内容变量拼到固定风格前缀后面。"""
    parts = [STYLE_PROMPT, ""]
    parts.append(f"Theme:\n{args.topic}")
    parts.append(f"Structure type:\n{args.structure}")
    parts.append(f"Core idea:\n{args.core_idea}")
    parts.append(f"Composition:\n{args.composition}")
    parts.append(f"Suggested elements:\n{args.elements}")
    parts.append(f"Chinese handwritten labels:\n{args.labels}")
    return "\n".join(parts)


def slugify(text):
    """中文/英文转安全文件名片段。"""
    s = re.sub(r"[^\w\u4e00-\u9fff]+", "-", text).strip("-")
    return s[:20] or "untitled"


def gen_one(args):
    token = os.environ.get("ARK_API_KEY")
    if not token:
        print("缺少环境变量 ARK_API_KEY。")
        print("请到火山方舟控制台创建 API Key，然后：")
        print("  set ARK_API_KEY=xxx")
        sys.exit(1)

    prompt = build_prompt(args)
    print(f"模型: {args.model}")
    print(f"seed: {args.seed if args.seed is not None else '随机（ARK 标准接口多不支持固定）'}")
    print(f"尺寸: {args.size}")
    print(f"prompt 前 80 字: {prompt[:80]}...")
    print("生成中（通常 5-20 秒）...")

    body = {
        "model": args.model,
        "prompt": prompt,
        "size": args.size,
        "response_format": "b64_json",
        "watermark": False,
    }
    if args.seed is not None:
        body["seed"] = args.seed
    if args.ref_image:
        # 支持单图或多图垫图（逗号分隔）
        refs = [load_ref_image(r.strip()) for r in args.ref_image.split(",") if r.strip()]
        body["image"] = refs if len(refs) > 1 else refs[0]
        print(f"参考图: {len(refs)} 张（垫图模式）")

    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        ARK_ENDPOINT,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "ignore")
        print(f"HTTP 错误 {e.code}: {detail}")
        sys.exit(2)
    except Exception as e:
        print(f"生图失败: {e}")
        sys.exit(2)

    # 解析返回：优先 b64_json，回退 url
    try:
        item = result["data"][0]
    except (KeyError, IndexError, TypeError):
        print("返回结构异常:", json.dumps(result, ensure_ascii=False)[:500])
        sys.exit(2)

    if item.get("b64_json"):
        img_bytes = base64.b64decode(item["b64_json"])
    elif item.get("url"):
        try:
            with urllib.request.urlopen(item["url"], timeout=60) as r:
                img_bytes = r.read()
        except Exception as e:
            print(f"下载结果图失败: {e}")
            sys.exit(2)
    else:
        print("返回中既无 b64_json 也无 url:", json.dumps(result, ensure_ascii=False)[:500])
        sys.exit(2)

    out_dir = Path("assets") / f"{slugify(args.topic)}-illustrations"
    out_dir.mkdir(parents=True, exist_ok=True)
    existing = sorted(out_dir.glob("*.png"))
    idx = len(existing) + 1
    out_path = out_dir / f"{idx:02d}-{slugify(args.topic)}.png"
    out_path.write_bytes(img_bytes)

    print(f"\n已保存: {out_path}")
    print("下一步：把这张图发给我看，我们一起调 IP / 构图 / 批注。")
    return out_path


def main():
    p = argparse.ArgumentParser(description="小鹿风格参数化生图（火山方舟 ARK + Seedream）")
    p.add_argument("--topic", required=True, help="配图主题，如 '穿搭打卡'")
    p.add_argument("--structure", required=True,
                   help="结构类型：Workflow/系统局部/前后对比/角色状态/概念隐喻/方法分层/地图路线/小漫画分镜")
    p.add_argument("--core-idea", required=True, help="这张图要表达的核心意思")
    p.add_argument("--composition", required=True, help="具体画面：角色在哪、做什么、主要物件、信息流向")
    p.add_argument("--elements", required=True, help="建议元素，用 / 分隔")
    p.add_argument("--labels", required=True, help="中文标注词，用 / 分隔，最多 5-8 个")
    p.add_argument("--model", default=DEFAULT_MODEL,
                   help=f"ARK 模型 ID，默认 {DEFAULT_MODEL}。可换 -5-0-pro-260628 / -4-5-251128 / -4-0-250828")
    p.add_argument("--size", default="2560x1440", help="输出尺寸，默认 2560x1440（16:9，2K）。Seedream 5.0 要求至少约369万像素")
    p.add_argument("--seed", type=int, default=None, help="随机种子，ARK 标准接口多不支持；支持时固定则可复现")
    p.add_argument("--ref-image", default=None,
                   help="参考图（垫图模式）：本地路径或公网URL，多张用逗号分隔。Seedream 会照参考图的角色画新场景")
    args = p.parse_args()
    gen_one(args)


if __name__ == "__main__":
    main()
