"""Submit, resume and download KomiAI image tasks using the Python standard library."""

import argparse
import http.client
import json
import mimetypes
import os
import re
import subprocess
import sys
import time
import uuid
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


API = "https://api.komiai.cn/tasks/v1"
MODEL = "gpt-image-2.5-sunburst-count"
CREDENTIAL_TARGET = "KomiAI.CodexImageGen/api.komiai.cn"
POLL_INTERVAL = 4
SIZES = (
    "auto", "1024x1024", "1536x1024", "1024x1536", "2048x2048",
    "2048x1152", "3840x2160", "2160x3840",
)
PENDING = {"created", "submitted", "queued", "processing"}
TASK_ID = re.compile(r"[A-Za-z0-9_-]+")
OPTIONS = ("size", "quality", "n", "background", "output_format", "output_compression", "moderation")


class TaskError(Exception):
    def __init__(self, message, *, retryable=False, uncertain=False):
        super().__init__(message)
        self.retryable = retryable
        self.uncertain = uncertain


class WindowsCredentialStore:
    GENERIC = 1
    PERSIST_LOCAL_MACHINE = 2
    ERROR_NOT_FOUND = 1168

    def __init__(self):
        import ctypes
        from ctypes import wintypes

        class Credential(ctypes.Structure):
            _fields_ = [
                ("Flags", wintypes.DWORD),
                ("Type", wintypes.DWORD),
                ("TargetName", wintypes.LPWSTR),
                ("Comment", wintypes.LPWSTR),
                ("LastWritten", wintypes.FILETIME),
                ("CredentialBlobSize", wintypes.DWORD),
                ("CredentialBlob", ctypes.POINTER(ctypes.c_ubyte)),
                ("Persist", wintypes.DWORD),
                ("AttributeCount", wintypes.DWORD),
                ("Attributes", ctypes.c_void_p),
                ("TargetAlias", wintypes.LPWSTR),
                ("UserName", wintypes.LPWSTR),
            ]

        credential_pointer = ctypes.POINTER(Credential)
        api = ctypes.WinDLL("Advapi32.dll", use_last_error=True)
        api.CredReadW.argtypes = [
            wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.POINTER(credential_pointer),
        ]
        api.CredReadW.restype = wintypes.BOOL
        api.CredWriteW.argtypes = [credential_pointer, wintypes.DWORD]
        api.CredWriteW.restype = wintypes.BOOL
        api.CredFree.argtypes = [ctypes.c_void_p]
        api.CredFree.restype = None
        self.api = api
        self.ctypes = ctypes
        self.credential = Credential
        self.credential_pointer = credential_pointer

    def read(self):
        pointer = self.credential_pointer()
        if not self.api.CredReadW(CREDENTIAL_TARGET, self.GENERIC, 0, self.ctypes.byref(pointer)):
            error = self.ctypes.get_last_error()
            if error == self.ERROR_NOT_FOUND:
                return ""
            raise self.ctypes.WinError(error)
        try:
            credential = pointer.contents
            if not credential.CredentialBlobSize:
                return ""
            blob = self.ctypes.string_at(credential.CredentialBlob, credential.CredentialBlobSize)
            return blob.decode("utf-8")
        finally:
            self.api.CredFree(pointer)

    def write(self, key):
        encoded = key.encode("utf-8")
        blob = (self.ctypes.c_ubyte * len(encoded)).from_buffer_copy(encoded)
        credential = self.credential(
            Type=self.GENERIC,
            TargetName=CREDENTIAL_TARGET,
            CredentialBlobSize=len(blob),
            CredentialBlob=blob,
            Persist=self.PERSIST_LOCAL_MACHINE,
        )
        try:
            if not self.api.CredWriteW(self.ctypes.byref(credential), 0):
                raise self.ctypes.WinError(self.ctypes.get_last_error())
        finally:
            self.ctypes.memset(blob, 0, len(blob))


def https_url(value):
    if not isinstance(value, str):
        return False
    try:
        url = urlsplit(value)
        return url.scheme == "https" and bool(url.hostname) and url.username is None
    except ValueError:
        return False


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class HTTPSRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not https_url(newurl):
            raise TaskError("KomiAI 图片下载被重定向到了无效的 HTTPS 地址。")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def object_json(raw):
    try:
        value = json.loads(raw)
    except ValueError:
        return {}
    return value if isinstance(value, dict) else {}


def retryable_code(code):
    return isinstance(code, int) and (code in (408, 429) or 500 <= code <= 599)


class KomiAI:
    def __init__(self, key):
        self.key = key
        self.api = build_opener(NoRedirect())
        self.media = build_opener(HTTPSRedirect())

    def request(self, route, *, body=None, content_type="application/json", timeout=60):
        headers = {"Authorization": f"Bearer {self.key}", "Accept": "application/json"}
        if body is not None:
            headers["Content-Type"] = content_type
        request = Request(API + route, data=body, headers=headers)
        try:
            with self.api.open(request, timeout=timeout) as response:
                payload = object_json(response.read())
        except HTTPError as exc:
            with exc:
                try:
                    detail = object_json(exc.read(65536)).get("message")
                except (OSError, http.client.HTTPException):
                    detail = None
            suffix = f"。{detail}" if isinstance(detail, str) and detail else ""
            raise TaskError(
                f"KomiAI 请求失败（HTTP {exc.code}）{suffix}",
                retryable=retryable_code(exc.code),
                uncertain=exc.code == 408 or 500 <= exc.code <= 599,
            ) from None
        except (OSError, http.client.HTTPException):
            raise TaskError("无法连接 KomiAI 或读取响应。", retryable=True, uncertain=True) from None

        code = payload.get("code")
        if code is None:
            raise TaskError("KomiAI 返回了无法识别的响应。", uncertain=True)
        if code != 200:
            raise TaskError(
                f"KomiAI 请求失败（业务码 {code}）。{payload.get('message') or ''}",
                retryable=retryable_code(code),
                uncertain=code == 408 or (isinstance(code, int) and 500 <= code <= 599),
            )
        data = payload.get("data")
        if not isinstance(data, dict):
            raise TaskError("KomiAI 成功响应缺少 data 对象。", uncertain=True)
        return data

    def upload(self, path):
        boundary = uuid.uuid4().hex
        media_type = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        suffix = path.suffix.lower()
        filename = "reference" + (suffix if re.fullmatch(r"\.[a-z0-9]+", suffix) else "")
        header = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
            f"Content-Type: {media_type}\r\n\r\n"
        ).encode("ascii")
        body = header + path.read_bytes() + f"\r\n--{boundary}--\r\n".encode("ascii")
        data = self.request("/upload", body=body, content_type=f"multipart/form-data; boundary={boundary}")
        url = data.get("downloadUrl")
        if not https_url(url):
            raise TaskError("临时文件上传响应缺少有效的 downloadUrl。")
        return url

    def submit(self, action, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        data = self.request(f"/openai/{MODEL}/{action}", body=body)
        task_id = data.get("id")
        if not isinstance(task_id, str) or not TASK_ID.fullmatch(task_id):
            raise TaskError("提交响应缺少有效的任务 ID。", uncertain=True)
        return task_id

    def wait(self, task_id, timeout):
        deadline = time.monotonic() + timeout
        last_status = None
        last_error = None
        while (remaining := deadline - time.monotonic()) > 0:
            try:
                data = self.request(f"/status/{task_id}", timeout=min(30, remaining))
            except TaskError as exc:
                if not exc.retryable:
                    raise
                last_error = str(exc)
            else:
                last_error = None
                status = data.get("status")
                if status == "completed":
                    urls = data.get("outputs")
                    if not isinstance(urls, list) or not urls or not all(map(https_url, urls)):
                        raise TaskError("任务已完成，但返回的图片链接缺失或无效。")
                    return urls
                if status == "failed":
                    raise TaskError(f"生成失败。{data.get('error') or '平台未提供失败原因。'}")
                if status == "canceled":
                    raise TaskError("任务已取消。")
                if not isinstance(status, str) or status not in PENDING:
                    raise TaskError(f"KomiAI 返回了未知任务状态 {status!r}。")
                if status != last_status:
                    emit("progress", task_id=task_id, status=status, stream=sys.stderr)
                    last_status = status
            time.sleep(min(POLL_INTERVAL, max(0, deadline - time.monotonic())))
        detail = f" 最近一次查询错误为 {last_error}" if last_error else ""
        raise TaskError("等待超时。可用原任务 ID 执行 resume 继续查询。" + detail)

    def download(self, url):
        try:
            with self.media.open(url, timeout=60) as response:
                return response.read()
        except HTTPError as exc:
            exc.close()
            raise TaskError(f"图片下载失败（HTTP {exc.code}）。可用原任务 ID 重新下载。") from None
        except (OSError, http.client.HTTPException):
            raise TaskError("图片下载连接中断。可用原任务 ID 重新下载。") from None


def image_extension(data):
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if data.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return ".webp"
    raise TaskError("下载内容缺少 PNG、JPEG 或 WebP 图片标识。")


def save_image(directory, stem, data):
    extension = image_extension(data)
    version = 1
    while True:
        name = stem if version == 1 else f"{stem}-v{version}"
        path = directory / (name + extension)
        try:
            output = path.open("xb")
        except FileExistsError:
            if path.is_file() and path.read_bytes() == data:
                return str(path)
            version += 1
            continue
        try:
            with output:
                output.write(data)
        except BaseException:
            path.unlink(missing_ok=True)
            raise
        return str(path)


def emit(event, *, stream=None, **data):
    print(json.dumps({"event": event, **data}, ensure_ascii=False), file=stream or sys.stdout, flush=True)


def local_file(value):
    path = Path(value)
    if not path.is_file():
        raise argparse.ArgumentTypeError("请提供存在的本地文件。")
    return path


def nonempty(value):
    if not value.strip():
        raise argparse.ArgumentTypeError("参数不能为空。")
    return value.strip()


def positive_seconds(value):
    seconds = int(value)
    if seconds <= 0:
        raise argparse.ArgumentTypeError("等待时间必须大于 0 秒。")
    return seconds


def prompt_for_mac_key(*, save=False):
    purpose = "Key 将保存到当前 macOS 用户的钥匙串。" if save else "Key 仅用于本次调用。"
    button = "保存" if save else "继续"
    script = (
        f'set response to display dialog "请输入 KomiAI API Key。{purpose}" '
        f'default answer "" with title "KomiAI API Key" buttons {{"取消", "{button}"}} '
        f'default button "{button}" cancel button "取消" with hidden answer\n'
        'return text returned of response'
    )
    unavailable = "无法打开 macOS 密码输入框。请在运行 Codex 的环境中设置 KOMIAI_API_KEY。"
    try:
        result = subprocess.run(
            ["/usr/bin/osascript", "-e", script], capture_output=True, encoding="utf-8", errors="replace",
        )
    except OSError:
        raise TaskError(unavailable) from None
    if result.returncode == 0:
        return result.stdout.strip()
    if "(-128)" in result.stderr:
        return ""
    raise TaskError(unavailable)


def prompt_for_key(*, save=False):
    if sys.platform == "darwin":
        return prompt_for_mac_key(save=save)
    unavailable = "当前环境无法打开密码输入框。请在运行 Codex 的环境中设置 KOMIAI_API_KEY。"
    try:
        import tkinter as tk
        from tkinter import ttk
    except ImportError:
        raise TaskError(unavailable) from None

    try:
        window = tk.Tk()
    except tk.TclError:
        raise TaskError(unavailable) from None

    key = ""
    try:
        window.title("KomiAI API Key")
        window.resizable(False, False)
        window.attributes("-topmost", True)
        frame = ttk.Frame(window, padding=18)
        frame.grid(sticky="nsew")
        purpose = "Key 将保存到当前 Windows 用户的凭据管理器。" if save else "Key 仅用于本次调用。"
        ttk.Label(frame, text=f"请输入 KomiAI API Key。{purpose}").grid(row=0, column=0, sticky="w")
        field = ttk.Entry(frame, width=48, show="*")
        field.grid(row=1, column=0, sticky="ew", pady=(8, 12))

        def submit(event=None):
            nonlocal key
            key = field.get().strip()
            if key:
                window.quit()

        buttons = ttk.Frame(frame)
        buttons.grid(row=2, column=0, sticky="e")
        ttk.Button(buttons, text="取消", command=window.quit).pack(side="left", padx=(0, 8))
        ttk.Button(buttons, text="保存" if save else "继续", command=submit).pack(side="left")
        window.protocol("WM_DELETE_WINDOW", window.quit)
        window.bind("<Return>", submit)
        window.bind("<Escape>", lambda event: window.quit())
        field.focus_set()
        window.mainloop()
    except tk.TclError:
        raise TaskError(unavailable) from None
    finally:
        window.destroy()
    return key


def ask_for_key(*, save=False):
    action = "输入并保存 Key" if save else "输入 Key"
    emit("awaiting_key", message=f"请在本机 KomiAI 密码输入框中{action}。", stream=sys.stderr)
    key = prompt_for_key(save=save)
    if not key:
        raise TaskError("已取消 Key 输入。")
    return key


def credential_store():
    if sys.platform == "win32":
        return WindowsCredentialStore()
    if sys.platform == "darwin":
        try:
            from mac_keychain import MacCredentialStore

            return MacCredentialStore(CREDENTIAL_TARGET)
        except (ImportError, AttributeError, ValueError, OSError) as exc:
            raise OSError("无法连接 macOS 钥匙串。") from exc
    return None


def save_api_key(store, key, *, stream=None):
    store.write(key)
    if store.read() != key:
        raise TaskError("保存后无法核对系统凭据。")
    emit("key_saved", message="KomiAI Key 已保存，后续调用可自动读取。", stream=stream)


def get_api_key(ask_key):
    key = os.environ.get("KOMIAI_API_KEY", "").strip()
    if key:
        return key
    store = None
    try:
        store = credential_store()
        key = store.read() if store is not None else ""
    except UnicodeError:
        key = ""
    except OSError:
        raise TaskError(
            "当前进程无法访问系统凭据。请从可访问当前用户凭据的本机环境重试，或设置 KOMIAI_API_KEY。"
        ) from None
    if key:
        return key
    if not ask_key:
        raise TaskError("缺少 KomiAI Key。请设置 KOMIAI_API_KEY，或允许本机密码输入框。")
    key = ask_for_key(save=store is not None)
    if store is not None:
        try:
            save_api_key(store, key, stream=sys.stderr)
        except (OSError, UnicodeError, TaskError):
            emit(
                "key_save_failed",
                message="系统未能保存 Key。当前任务会继续，后续调用可能需要重新输入。",
                stream=sys.stderr,
            )
    return key


def configure_key():
    store = credential_store()
    if store is None:
        raise TaskError("请在运行环境中设置 KOMIAI_API_KEY。")
    save_api_key(store, ask_for_key(save=True))


def parse_args(argv):
    parser = argparse.ArgumentParser(description="Generate, edit or resume KomiAI image tasks.")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("configure-key", help="Save or replace the KomiAI Key in your system credential store.")
    for command in ("generate", "edit", "resume"):
        sub = commands.add_parser(command)
        sub.add_argument("--out-dir", type=Path, default=Path("outputs/komiai"))
        sub.add_argument("--timeout", type=positive_seconds, default=600)
        sub.add_argument(
            "--ask-key", action=argparse.BooleanOptionalAction, default=True,
            help="Prompt for and save a missing Key on Windows or macOS (default: enabled).",
        )
        if command == "resume":
            sub.add_argument("--task-id", required=True)
            continue
        sub.add_argument("--prompt-file", type=local_file, required=True)
        sub.add_argument("--size", choices=SIZES)
        sub.add_argument("--quality", choices=("auto", "low", "medium", "high"))
        sub.add_argument("--n", type=int, choices=range(1, 11))
        sub.add_argument("--background", choices=("auto", "transparent", "opaque"))
        sub.add_argument("--output-format", choices=("png", "jpeg", "webp"))
        sub.add_argument("--output-compression", type=int, metavar="0-100")
        sub.add_argument("--moderation", choices=("auto", "low"))
        sub.add_argument("--request-id", type=nonempty)
        if command == "edit":
            sub.add_argument("--reference", dest="references", action="append", type=nonempty)
            sub.add_argument("--reference-file", dest="references", action="append", type=local_file)
            mask = sub.add_mutually_exclusive_group()
            mask.add_argument("--mask", type=nonempty)
            mask.add_argument("--mask-file", dest="mask", type=local_file)
            sub.add_argument("--input-fidelity", choices=("low", "high"))

    args = parser.parse_args(argv)
    if args.command == "configure-key":
        return args
    if args.command == "resume":
        if not TASK_ID.fullmatch(args.task_id):
            parser.error("--task-id 必须是 KomiAI 在提交响应中返回的任务 ID。")
        return args
    if args.command == "edit" and not 1 <= len(args.references or []) <= 16:
        parser.error("edit 需要 1 至 16 张参考图。")
    if args.background == "transparent" and args.output_format == "jpeg":
        parser.error("透明背景请选择 PNG 或 WebP。")
    if args.output_compression is not None:
        if not 0 <= args.output_compression <= 100:
            parser.error("--output-compression 必须在 0 至 100 之间。")
        if args.output_format not in ("jpeg", "webp"):
            parser.error("--output-compression 需要 JPEG 或 WebP。")
    return args


def submit_image(client, args, request_id):
    prompt = args.prompt_file.read_text(encoding="utf-8-sig")
    if not prompt.strip():
        raise TaskError("提示词文件为空。")
    payload = {"prompt": prompt, "request_id": request_id}
    payload.update({name: getattr(args, name) for name in OPTIONS if getattr(args, name) is not None})
    action = "text-to-image"
    if args.command == "edit":
        action = "image-edit"
        payload["reference_image"] = [
            client.upload(source) if isinstance(source, Path) else source for source in args.references
        ]
        if args.mask is not None:
            payload["mask"] = client.upload(args.mask) if isinstance(args.mask, Path) else args.mask
        if args.input_fidelity is not None:
            payload["input_fidelity"] = args.input_fidelity
    emit("submitting", request_id=request_id, stream=sys.stderr)
    try:
        return client.submit(action, payload)
    except TaskError as exc:
        if exc.uncertain:
            raise TaskError(f"提交结果不明。先核对原请求，避免重复生成。{exc}") from None
        raise
    except KeyboardInterrupt:
        raise TaskError("提交已中断，结果不明。先核对原请求，避免重复生成。") from None


def main(argv=None):
    args = parse_args(argv)
    key = ""
    task_id = getattr(args, "task_id", None)
    request_id = None
    files = []
    try:
        if args.command == "configure-key":
            configure_key()
            return 0
        key = get_api_key(args.ask_key)
        directory = args.out_dir.resolve()
        directory.mkdir(parents=True, exist_ok=True)
        client = KomiAI(key)
        if task_id is None:
            request_id = args.request_id or f"komiai-image-{uuid.uuid4().hex}"
            task_id = submit_image(client, args, request_id)
            emit("accepted", request_id=request_id, task_id=task_id, stream=sys.stderr)
        for index, url in enumerate(client.wait(task_id, args.timeout), 1):
            files.append(save_image(directory, f"{task_id}-{index:02d}", client.download(url)))
    except (TaskError, OSError, UnicodeError, KeyboardInterrupt) as exc:
        message = str(exc) or "运行已中断。"
        if key:
            message = message.replace(key, "[API key]")
        message = re.sub(r"https?://[^\s<>\"]+", "[URL]", message)
        emit("error", message=message, request_id=request_id, task_id=task_id, files=files, stream=sys.stderr)
        return 1
    emit("completed", request_id=request_id, task_id=task_id, files=files)
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
    raise SystemExit(main())
