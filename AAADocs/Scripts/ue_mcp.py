"""直接调用编辑器内 ModelContextProtocol 服务（Streamable HTTP）的最小客户端。

用途：编辑器重启后 IDE 侧 MCP 会话失效时，脚本仍能在用户打开的那个编辑器里执行工具，
不必另起无头进程写资产。

    from ue_mcp import Mcp
    m = Mcp()                                   # 初始化新会话
    m.call("describe_toolset", toolset_name="...")          # 顶层工具
    m.tool("editor_toolset.toolsets.asset.AssetTools.exists", path="/Game/X")  # 工具集工具
    m.script(PY)                                 # ProgrammaticToolset.execute_tool_script

命令行：python ue_mcp.py <tool_name> '<json args>' [toolset]
工具返回 isError 时抛 RuntimeError，不吞错误。
"""
import json
import sys
import time
import urllib.request

URL = "http://127.0.0.1:8000/mcp"


class Mcp:
    def __init__(self, url=URL):
        self.url, self.sid, self.n = url, None, 0
        self._rpc("initialize", {"protocolVersion": "2025-03-26", "capabilities": {},
                                 "clientInfo": {"name": "ggygo-script", "version": "1"}})
        self._post({"jsonrpc": "2.0", "method": "notifications/initialized"})

    def _post(self, body):
        req = urllib.request.Request(self.url, data=json.dumps(body).encode(), method="POST", headers={
            "Content-Type": "application/json", "Accept": "application/json, text/event-stream",
            **({"Mcp-Session-Id": self.sid} if self.sid else {})})
        with urllib.request.urlopen(req, timeout=1800) as r:
            self.sid = r.headers.get("Mcp-Session-Id") or self.sid
            raw = r.read().decode("utf-8")
        if not raw.strip():
            return None
        if raw.lstrip().startswith("{"):
            return json.loads(raw)
        # text/event-stream：取最后一个 data 行
        data = [l[5:].strip() for l in raw.splitlines() if l.startswith("data:")]
        return json.loads(data[-1]) if data else None

    def _rpc(self, method, params):
        self.n += 1
        res = self._post({"jsonrpc": "2.0", "id": self.n, "method": method, "params": params})
        if res is None:
            raise RuntimeError("%s 无响应" % method)
        if "error" in res:
            raise RuntimeError("%s: %s" % (method, res["error"]))
        return res["result"]

    def describe(self, toolset_name):
        return self.raw("describe_toolset", toolset_name=toolset_name)

    def raw(self, name, **arguments):
        """调用服务直接暴露的 MCP 工具（list_toolsets / describe_toolset / call_tool）。"""
        res = self._rpc("tools/call", {"name": name, "arguments": arguments})
        text = "".join(c.get("text", "") for c in res.get("content", []))
        if res.get("isError"):
            raise RuntimeError(text)
        try:
            return json.loads(text)
        except ValueError:
            return text

    def call(self, tool_name, toolset_name=None, **arguments):
        args = {"tool_name": tool_name, "arguments": arguments}
        if toolset_name:
            args["toolset_name"] = toolset_name
        res = self._rpc("tools/call", {"name": "call_tool", "arguments": args})
        text = "".join(c.get("text", "") for c in res.get("content", []))
        if res.get("isError"):
            raise RuntimeError(text)
        try:
            return json.loads(text)
        except ValueError:
            return text

    PIE_TOOL = "EditorToolset.EditorAppToolset.IsPIERunning"

    def wait_not_pie(self, timeout=1800):
        """编辑器在 PIE 时 EditorAssetSubsystem 拒绝资产读写（does_asset_exist 恒为 False），
        别的会话可能正在用同一编辑器跑测试，这里等它结束而不是去停掉它。超时报错。"""
        start = time.time()
        warned = False
        while self.call("IsPIERunning", "EditorToolset.EditorAppToolset")["returnValue"]:
            if not warned:
                print("[ue_mcp] 编辑器正在 PIE，等待结束……", flush=True)
                warned = True
            if time.time() - start > timeout:
                raise RuntimeError("编辑器 PIE 超过 %d 秒未结束" % timeout)
            time.sleep(5)
        self._pie_checked = time.time()

    def tool(self, full_name, **arguments):
        toolset, name = full_name.rsplit(".", 1)
        if full_name != self.PIE_TOOL and time.time() - getattr(self, "_pie_checked", 0) > 3:
            self.wait_not_pie()
        return self.call(name, toolset, **arguments)

    def script(self, code):
        out = self.tool("editor_toolset.toolsets.programmatic.ProgrammaticToolset.execute_tool_script", script=code)
        return json.loads(out["returnValue"]) if isinstance(out, dict) and "returnValue" in out else out


if __name__ == "__main__":
    m = Mcp()
    print(json.dumps(m.call(sys.argv[1], sys.argv[3] if len(sys.argv) > 3 else None,
                            **(json.loads(sys.argv[2]) if len(sys.argv) > 2 else {})), ensure_ascii=False, indent=1))
