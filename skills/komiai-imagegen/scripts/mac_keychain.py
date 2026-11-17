"""Store the KomiAI credential using macOS Keychain Services."""

import ctypes
from contextlib import contextmanager


class MacCredentialStore:
    ACCOUNT = "KOMIAI_API_KEY"
    UTF8 = 0x08000100
    ITEM_NOT_FOUND = -25300
    DUPLICATE_ITEM = -25299

    def __init__(self, service):
        self.service = service
        self.core = ctypes.CDLL("/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation")
        self.security = ctypes.CDLL("/System/Library/Frameworks/Security.framework/Security")
        pointer = ctypes.c_void_p
        pointer_array = ctypes.POINTER(pointer)
        index = ctypes.c_long
        status = ctypes.c_int32
        self._bind(self.core.CFStringCreateWithCString, pointer, pointer, ctypes.c_char_p, ctypes.c_uint32)
        self._bind(self.core.CFDataCreate, pointer, pointer, ctypes.c_char_p, index)
        self._bind(self.core.CFDataGetLength, index, pointer)
        self._bind(self.core.CFDataGetBytePtr, pointer, pointer)
        self._bind(
            self.core.CFDictionaryCreate, pointer, pointer, pointer_array, pointer_array, index, pointer, pointer,
        )
        self._bind(self.core.CFRelease, None, pointer)
        self._bind(self.security.SecItemCopyMatching, status, pointer, pointer_array)
        self._bind(self.security.SecItemAdd, status, pointer, pointer_array)
        self._bind(self.security.SecItemUpdate, status, pointer, pointer)
        self.key_callbacks = ctypes.addressof(ctypes.c_char.in_dll(self.core, "kCFTypeDictionaryKeyCallBacks"))
        self.value_callbacks = ctypes.addressof(ctypes.c_char.in_dll(self.core, "kCFTypeDictionaryValueCallBacks"))
        self.true = ctypes.c_void_p.in_dll(self.core, "kCFBooleanTrue").value

    @staticmethod
    def _bind(function, result_type, *argument_types):
        function.restype = result_type
        function.argtypes = argument_types

    def _symbol(self, name):
        return ctypes.c_void_p.in_dll(self.security, name).value

    @contextmanager
    def _owned(self, pointer):
        if not pointer:
            raise OSError("无法创建 macOS 钥匙串操作所需的数据。")
        try:
            yield pointer
        finally:
            self.core.CFRelease(pointer)

    @contextmanager
    def _identity(self):
        with (
            self._owned(self.core.CFStringCreateWithCString(None, self.service.encode("utf-8"), self.UTF8)) as service,
            self._owned(self.core.CFStringCreateWithCString(None, self.ACCOUNT.encode("utf-8"), self.UTF8)) as account,
        ):
            yield {
                self._symbol("kSecClass"): self._symbol("kSecClassGenericPassword"),
                self._symbol("kSecAttrService"): service,
                self._symbol("kSecAttrAccount"): account,
            }

    def _dictionary(self, values):
        array_type = ctypes.c_void_p * len(values)
        pointer = self.core.CFDictionaryCreate(
            None, array_type(*values), array_type(*values.values()), len(values),
            self.key_callbacks, self.value_callbacks,
        )
        return self._owned(pointer)

    def read(self):
        result = ctypes.c_void_p()
        with self._identity() as identity:
            query = {**identity, self._symbol("kSecReturnData"): self.true}
            with self._dictionary(query) as parameters:
                status = self.security.SecItemCopyMatching(parameters, ctypes.byref(result))
        if status == self.ITEM_NOT_FOUND:
            return ""
        if status:
            raise OSError(f"macOS 钥匙串读取失败（状态码 {status}）。")
        with self._owned(result) as data:
            length = self.core.CFDataGetLength(data)
            return ctypes.string_at(self.core.CFDataGetBytePtr(data), length).decode("utf-8")

    def write(self, key):
        encoded = key.encode("utf-8")
        with (
            self._identity() as identity,
            self._owned(self.core.CFDataCreate(None, encoded, len(encoded))) as data,
        ):
            value = {self._symbol("kSecValueData"): data}
            with self._dictionary({**identity, **value}) as attributes:
                status = self.security.SecItemAdd(attributes, None)
            if status == self.DUPLICATE_ITEM:
                with self._dictionary(identity) as query, self._dictionary(value) as changes:
                    status = self.security.SecItemUpdate(query, changes)
            if status:
                raise OSError(f"macOS 钥匙串保存失败（状态码 {status}）。")
