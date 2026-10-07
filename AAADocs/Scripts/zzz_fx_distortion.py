"""Offline original distortion composite contract; no editor or source mutation.

The field producer is planned by zzz_fx_material with output_contract set to
distortion_field. This module retains the actual D3D11 consumer instructions.
Render resources, samplers and the original RGB shift are mandatory runtime
inputs. Their integration and values remain unverified until separately supplied.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

import zzz_dxbc_hlsl as T


class DistortionError(ValueError):
    pass


def composite_offsets(uv, accumulated_field, rgb_shift):
    """Direct source formula, useful for reviewing author-supplied RGB shifts.

    Sample the accumulated field once. Compositing each particle independently
    changes overlapping effects because the consumer multiplies field.xy by z.
    No runtime RGB shift is guessed here.
    """
    if len(uv) != 2 or len(accumulated_field) != 4 or len(rgb_shift) != 3:
        raise DistortionError("Expected UV2, accumulated RGBA4 and explicit RGBShift3")
    values = list(uv) + list(accumulated_field) + list(rgb_shift)
    if not all(isinstance(x, (int, float)) and math.isfinite(x) for x in values):
        raise DistortionError("Distortion inputs must be finite numbers")
    q = tuple(0.1 * x for x in accumulated_field[:2])
    return tuple(tuple(uv[k] + q[k] + q[k] * accumulated_field[2] * shift
                       for k in range(2)) for shift in rgb_shift)


def consumer_plan(shader_path):
    source = Path(shader_path)
    shader = T.parse_shader(source.read_text(encoding="utf-8"))
    passes = [p for p in shader["passes"] if p["fp"]]
    if len(passes) != 1:
        raise DistortionError("Expected one original D3D11 DistortionBlit consumer")
    fp = passes[0]["fp"]
    names = {t["name"] for t in fp["bind"]["tex"].values()}
    if names != {"_MainTex", "_CameraDistortionTextureOverlay"}:
        raise DistortionError("Unverified distortion consumer textures: " + repr(names))
    if fp["keywords"] or [(r["reg"], r["mask"]) for r in fp["out"]] != [(0, "xyzw")]:
        raise DistortionError("Unverified distortion consumer variant/output")
    provider = {
        "_DistortionRgbShift": {"rows": ["float4(RGBShift, 0.0)"], "comps": "xyz"},
        "__textures__": {
            "_MainTex": "SceneTexture.SampleLevel(SceneSampler, {uv}, 0.0)",
            "_CameraDistortionTextureOverlay": "FieldTexture.SampleLevel(FieldSampler, {uv}, 0.0)",
        },
    }
    translated = T.translate(fp, "b", provider, {0: "xyzw"})
    if set(translated["live_inputs"]) != {("v0", "x"), ("v0", "y")}:
        raise DistortionError("Unverified distortion consumer screen inputs")
    if translated["mat_params"] or translated["textures"]:
        raise DistortionError("Distortion consumer has unbound material inputs")
    code = ("float4 ZZZCompositeDistortion(float2 ViewportUV, float3 RGBShift,\n"
            "    Texture2D SceneTexture, SamplerState SceneSampler,\n"
            "    Texture2D FieldTexture, SamplerState FieldSampler)\n{\n"
            "    uint4 bv0 = asuint(float4(ViewportUV, 0.0, 0.0));\n"
            + translated["code"] + "\n    return asfloat(bo0);\n}\n")
    return {
        "shader": "Hidden/Universal Render Pipeline/DistortionBlit",
        "source": str(source), "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "output_contract": "scene_composite", "code": code,
        "required_inputs": ["ViewportUV", "RGBShift", "SceneTexture", "SceneSampler", "FieldTexture", "FieldSampler"],
        "resource_contract": {
            "field": "Additively accumulated signed RGBA field; zero clear; no color conversion or tone mapping",
            "scene": "Source scene color with the same viewport and source-consumer render stage; mip zero",
            "uv": "Consumer uses direct normalized screen UV; viewport/buffer mapping must be supplied at the view integration seam",
            "rgb_shift": "Explicit original runtime value or a user-approved authored setting; no default",
            "samplers": "Explicit resource sampler states; original runtime bindings require verification",
        },
        "runtime_binding": "unverified", "visual_comparison": "unverified",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("consumer_shader", type=Path)
    args = parser.parse_args()
    print(json.dumps(consumer_plan(args.consumer_shader), ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
