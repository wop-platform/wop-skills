// commit-and-tag-version 自定义 updater：.cursor-plugin/marketplace.json 的版本
// 嵌在 metadata.version，默认 json updater 只写顶层 version（会留下旧
// metadata.version 并多出一个顶层键）——探针已复现，故单独接线。
module.exports = {
  readVersion(contents) {
    return JSON.parse(contents).metadata.version;
  },
  writeVersion(contents, version) {
    const data = JSON.parse(contents);
    data.metadata.version = version;
    return JSON.stringify(data, null, 2) + "\n";
  },
};
