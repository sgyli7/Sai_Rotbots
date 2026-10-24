# 038 原生重建包下载

此包保留038候选的全部原始输入和相对重建入口。整机仍未通过外观和工程验收。

传输通道的单次64 MiB帧限制要求分为两卷。下载到同一目录：

- [第1卷](goose_061_native_sources.tar.xz.part01)
- [第2卷](goose_061_native_sources.tar.xz.part02)

按顺序合并，恢复的文件为64,212,076字节：

```bash
cat goose_061_native_sources.tar.xz.part01 goose_061_native_sources.tar.xz.part02 > goose_061_native_sources.tar.xz
sha256sum goose_061_native_sources.tar.xz
tar -xJf goose_061_native_sources.tar.xz
```

完整文件SHA256：`1f7798cc07569b0a6f006e24a059a6de72ddeb290b094e24707242209320d253`。解压后按包内README运行相对重建入口；历史参数特征树不完整。分卷只改变传输布局，原归档字节、几何和验证身份不变。
