"""按材质的启用关键字导出它实际使用的 Shader 变体反汇编文本。

AnimeStudio 的 ANIMESTUDIO_SHADER_KEYWORDS 只输出与关键字集合匹配的子程序（见 ShaderConverter.SelectVariant），
大型 uber Shader（Particles_Dissolve_CustomColor_Mask 有上万个变体）不必全量反汇编。

用法：python zzz_shader_variants.py <material.json> [更多 material.json ...]
输出：<VARIANT_ROOT>/<Shader 名>/<关键字摘要>/Shader/<Shader 文件>.shader，并打印路径。
同一 Shader + 关键字集合只导出一次。
"""
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import zzz_assetmap as A  # noqa: E402

CLI = r"F:\AnimeStudio\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe"
BLOCKS = Path(r"F:\ZenlessZoneZero Game\ZenlessZoneZero_Data\StreamingAssets\Blocks")
VARIANT_ROOT = Path(r"F:\AnimeStudio\Exports\Shader\ZZZ_20260925\FXVariants")


def variant_dir(shader_name, keywords):
    tag = hashlib.md5(" ".join(keywords).encode()).hexdigest()[:8] if keywords else "none"
    return VARIANT_ROOT / shader_name.replace("/", "_").replace(" ", "_") / tag


def export_variant(material_path):
    m = json.load(open(material_path, encoding="utf-8"))
    keywords = sorted((m.get("m_ShaderKeywords") or "").split())
    hits = A.lookup(m["m_Shader"]["m_PathID"], "Shader")
    if not hits:
        raise SystemExit("AssetMap 中找不到 Shader PathID=%d（%s）" % (m["m_Shader"]["m_PathID"], material_path))
    shader_name, block = hits[0][1], Path(hits[0][2]).stem
    out = variant_dir(shader_name, keywords)
    files = list(out.glob("Shader/*.shader"))
    if not files:
        env = dict(os.environ, ANIMESTUDIO_SHADER_KEYWORDS=" ".join(keywords) or "NONE")
        subprocess.run([CLI, str(BLOCKS / (block + ".blk")), str(out), "--game", "ZZZ", "--types", "Shader",
                        "--names", "^" + shader_name.replace("(", r"\(").replace(")", r"\)") + "$", "--silent"],
                       check=True, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        (out / "keywords.txt").write_text(" ".join(keywords), encoding="utf-8")
        files = list(out.glob("Shader/*.shader"))
    if len(files) != 1:
        raise SystemExit("%s 导出结果异常: %s" % (shader_name, files))
    return shader_name, keywords, files[0]


def main():
    for p in sys.argv[1:]:
        name, kw, f = export_variant(p)
        print("%s | %s | %s" % (name, " ".join(kw) or "-", f))


if __name__ == "__main__":
    main()
