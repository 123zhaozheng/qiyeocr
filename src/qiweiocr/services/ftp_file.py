from __future__ import annotations

import asyncio
import base64
import logging
import posixpath
from ftplib import FTP
from ftplib import FTP_TLS
from ftplib import all_errors
from io import BytesIO

logger = logging.getLogger(__name__)


class FtpDownloadError(RuntimeError):
    pass


class FtpFileService:
    def __init__(
        self,
        host: str,
        port: int,
        username: str | None,
        password: str | None,
        base_dir: str | None,
        timeout_seconds: float,
        passive: bool,
        use_tls: bool,
        encoding: str,
    ) -> None:
        self.host = host.strip()
        self.port = port
        self.username = username
        self.password = password
        self.base_dir = self._normalize_base_dir(base_dir)
        self.timeout_seconds = timeout_seconds
        self.passive = passive
        self.use_tls = use_tls
        self.encoding = encoding

    async def download_base64(self, remote_path: str) -> str:
        data = await asyncio.to_thread(self._download_bytes, remote_path)
        return base64.b64encode(data).decode("ascii")

    def _download_bytes(self, remote_path: str) -> bytes:
        if not self.host:
            raise FtpDownloadError("FTP host is not configured")

        target_path = self._resolve_remote_path(remote_path)
        logger.info("[FTP] 开始下载文件 | host=%s | path=%s", self.host, target_path)

        buffer = BytesIO()
        ftp = self._create_client()
        try:
            ftp.connect(self.host, self.port, timeout=self.timeout_seconds)
            ftp.login(self.username, self.password)
            ftp.set_pasv(self.passive)
            if isinstance(ftp, FTP_TLS):
                ftp.prot_p()
            ftp.retrbinary(f"RETR {target_path}", buffer.write)
            data = buffer.getvalue()
            if not data:
                raise FtpDownloadError(f"FTP file is empty: {target_path}")
            logger.info("[FTP] 文件下载完成 | path=%s | bytes=%d", target_path, len(data))
            return data
        except FtpDownloadError:
            raise
        except all_errors as exc:
            raise FtpDownloadError(f"FTP download failed for path '{target_path}': {exc}") from exc
        finally:
            try:
                ftp.quit()
            except all_errors:
                ftp.close()

    def _create_client(self) -> FTP:
        client: FTP = FTP_TLS() if self.use_tls else FTP()
        client.encoding = self.encoding
        return client

    def _resolve_remote_path(self, remote_path: str) -> str:
        cleaned = remote_path.strip()
        if not cleaned:
            raise FtpDownloadError("FTP remote path is empty")

        if cleaned.startswith("/"):
            normalized = posixpath.normpath(cleaned)
            if normalized in {".", "/"}:
                raise FtpDownloadError(f"Invalid FTP path: {remote_path}")
            return normalized

        normalized = posixpath.normpath(cleaned)
        if normalized.startswith("../") or normalized == "..":
            raise FtpDownloadError(f"FTP path escapes base directory: {remote_path}")

        if self.base_dir:
            target = posixpath.normpath(posixpath.join(self.base_dir, normalized))
            if target != self.base_dir and not target.startswith(f"{self.base_dir}/"):
                raise FtpDownloadError(f"FTP path escapes base directory: {remote_path}")
            return target

        if normalized in {".", "/"}:
            raise FtpDownloadError(f"Invalid FTP path: {remote_path}")
        return normalized

    @staticmethod
    def _normalize_base_dir(base_dir: str | None) -> str | None:
        if not base_dir:
            return None
        normalized = posixpath.normpath(base_dir.strip())
        if normalized in {".", ""}:
            return None
        return normalized if normalized.startswith("/") else f"/{normalized}"
