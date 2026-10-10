# 读取当前解释器已安装的依赖元数据，离线复用不访问其他项目源码。
from importlib.metadata import distribution
# Wheel记录使用CSV，文件路径不经过shell解释。
import csv
# Wheel的哈希使用URL安全的Base64。
import base64
# 每个文件记录真实SHA256，供安装工具校验。
import hashlib
# 内存缓冲避免产生额外临时正文。
import io
# 输出路径由调用方明确传入。
from pathlib import Path
# Wheel是标准ZIP容器，保留依赖的许可和动态库。
import zipfile

# 将已安装的正规依赖重组为离线wheel；排除安装机器专用记录。
def cache_installed_wheel(package_name: str, output_directory: Path) -> Path:
    # distribution不存在时明确抛错，不自动下载替代版本。
    package = distribution(package_name)
    # 获取发布时的wheel标签，不凭本机平台猜测二进制兼容性。
    metadata = package.read_text("WHEEL")
    # 已安装依赖必须有标准wheel元数据。
    if metadata is None:
        # 非wheel安装没有足够依据生成可安装缓存。
        raise ValueError(f"{package_name}: 缺少WHEEL元数据")
    # 取已验证wheel中的兼容标签。
    tag = next(line[5:] for line in metadata.splitlines() if line.startswith("Tag: "))
    # 规范化发行名与版本，生成标准文件名。
    filename = f"{package.metadata['Name'].replace('-', '_')}-{package.version}-{tag}.whl"
    # 只在调用方的输出区创建缓存。
    output_directory.mkdir(parents=True, exist_ok=True)
    # 每次构建写到独立文件，失败不会覆盖其他产物。
    target = output_directory / filename
    # 文件与记录独立持有，不复用已安装RECORD中的私人路径。
    records = []
    # 在wheel中保留唯一的dist-info记录路径。
    record_path = ""
    # 开始归档标准依赖文件。
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        # 只从依赖声明的安装文件清单读取。
        for item in package.files or ():
            # 标准化为相对wheel路径。
            name = item.as_posix()
            # RECORD稍后用实际内容重建。
            if name.endswith(".dist-info/RECORD"):
                # 保存记录位置而不复制旧机器清单。
                record_path = name
                # 当前项由末尾统一生成。
                continue
            # 排除机器安装标记、字节码和越界脚本路径。
            if ".." in item.parts or "__pycache__" in item.parts or item.name in {
                "INSTALLER", "REQUESTED", "direct_url.json"} or name.endswith(".pyc"):
                # 这些文件不是依赖运行和许可所需资源。
                continue
            # 从声明文件读取字节，缺失时构建明确失败。
            content = Path(package.locate_file(item)).read_bytes()
            # 将依赖原始运行文件写入缓存，不改正文。
            archive.writestr(name, content)
            # 计算真实内容哈希，去除Base64尾部填充符合wheel格式。
            digest = base64.urlsafe_b64encode(hashlib.sha256(content).digest()).rstrip(b"=").decode("ascii")
            # 记录相对路径、哈希和字节数。
            records.append((name, f"sha256={digest}", len(content)))
        # 缺少标准记录路径时拒绝生成假wheel。
        if not record_path:
            # 保留原因而不继续安装不完整文件。
            raise ValueError(f"{package_name}: 缺少RECORD路径")
        # RECORD自身的哈希和大小留空。
        records.append((record_path, "", ""))
        # 使用CSV正确转义路径中的特殊字符。
        buffer = io.StringIO(newline="")
        # 全部记录在内存写成标准CSV。
        csv.writer(buffer).writerows(records)
        # 在归档末尾加入新记录。
        archive.writestr(record_path, buffer.getvalue())
    # 返回实际生成的依赖缓存。
    return target
