"""@file minimal_multiplayer_input.py
@brief 消费现有桥接的原装配数字键操作；自然帧与动作观察由原 host 负责。

模块导入不连接 UE。首次 Ready 固定原对象和 opaque User/Device；后继装配不接管。
返回值只描述软件键提交。
"""

from dataclasses import dataclass


class InputOperationError(RuntimeError):
    """原装配、设备或反射协议不能继续消费。"""


@dataclass(frozen=True)
class OriginalInputAssembly:
    """同一次 Ready 的真实对象及原生 opaque 值；不保存内部 ID。"""

    world: object
    local_player: object
    player_controller: object
    pawn: object
    player_input: object
    pawn_input_component: object
    platform_user: object
    input_device: object


def pin_ready_assembly(ue, world, local_player):
    """读取调用者已核来源的 World/LocalPlayer，不枚举 Actor 或选择槽位。"""
    result = ue.GGYGOPlayerInputBridgeLibrary.read_local_player_input_assembly(
        world, local_player)
    if not isinstance(result, tuple) or len(result) != 8:
        raise InputOperationError("ReadLocalPlayerInputAssembly 未返回八元组。")
    status, pc, pawn, player_input, component, user, device, diagnostic = result
    if not isinstance(diagnostic, str):
        raise InputOperationError("装配诊断不是 字符串协议。")
    if status != ue.GGYGOPlayerInputAssemblyStatus.READY:
        raise InputOperationError("原输入装配未 Ready：" + diagnostic)
    return OriginalInputAssembly(world, local_player, pc, pawn, player_input,
                                 component, user, device)


def read_mapped_key(context, expected_action, key_name):
    """返回已加载 IMC 中唯一精确 Action/键名行的原 FKey，不构造默认键。"""
    rows = context.get_editor_property("default_key_mappings").get_editor_property("mappings")
    keys = [row.get_editor_property("key") for row in rows
            if row.get_editor_property("action") == expected_action
            and str(row.get_editor_property("key").get_editor_property("key_name")) == key_name]
    if len(keys) != 1:
        raise InputOperationError("IMC 的精确 Action/键名行数量不是一：" + key_name)
    return keys[0]


def _native_device_call(ue, name, *args):
    """使用引擎原 UFUNCTION 名，避免猜测 opaque 值的字段或 Python 方法别名。"""
    return ue.get_default_object(ue.InputDeviceLibrary).call_method(name, args=args)


def _native_bool(ue, name, *args):
    result = _native_device_call(ue, name, *args)
    if type(result) is not bool:
        raise InputOperationError(name + " 未返回原生 bool。")
    return result


def _read_original_device_facts(ue, original):
    """fresh 装配核对后仍保留首次设备；当前 primary 变化只作为事实返回。"""
    current = pin_ready_assembly(ue, original.world, original.local_player)
    for name in ("player_controller", "pawn", "player_input", "pawn_input_component"):
        if getattr(current, name) != getattr(original, name):
            raise InputOperationError("原装配已更换：" + name + "；不向后继提交或清理。")
    if not _native_bool(ue, "EqualEqual_PlatformUserId", current.platform_user, original.platform_user):
        raise InputOperationError("原 LocalPlayer 平台用户已更换。")
    if not _native_bool(ue, "IsValidPlatformId", original.platform_user):
        raise InputOperationError("原平台用户值无效；不补造 ID。")
    if not _native_bool(ue, "IsValidInputDevice", original.input_device):
        raise InputOperationError("首次 Ready 的原设备值无效；不采用默认或后继设备。")
    device_user = _native_device_call(ue, "GetUserForInputDevice", original.input_device)
    if not _native_bool(ue, "EqualEqual_PlatformUserId", device_user, original.platform_user):
        raise InputOperationError("原设备已不属于原平台用户。")
    return {
        "primary_device_unchanged": _native_bool(
            ue, "EqualEqual_InputDeviceId", current.input_device, original.input_device),
        "connection_state": _native_device_call(
            ue, "GetInputDeviceConnectionState", original.input_device),
    }


def submit_digital_key(ue, original, key, pressed):
    """分帧调用本函数；handled 不表示 IA/ASC 消费、qualified Held 或能力完成。"""
    if type(pressed) is not bool:
        raise InputOperationError("pressed 必须为明确的 bool。")
    device_facts = _read_original_device_facts(ue, original)
    result = ue.GGYGOPlayerInputBridgeLibrary.submit_digital_key_event(
        original.world, original.local_player, original.player_controller,
        original.pawn, original.player_input, original.pawn_input_component,
        original.input_device, key, pressed)
    if result is None:
        # UE Python 的 bool 成功 gate 隐去了 false 分支的所有 out 参数。
        raise InputOperationError(
            "SubmitDigitalKeyEvent 返回 None：未提交；Python 未暴露该分支原生 out 诊断。")
    if (not isinstance(result, tuple) or len(result) != 2
            or type(result[0]) is not bool or not isinstance(result[1], str)):
        raise InputOperationError("Submit 返回形态不符 二元组；提交状态未能解析。")
    handled, diagnostic = result
    return {"submitted": True, "handled": handled, "diagnostic": diagnostic,
            **device_facts}
