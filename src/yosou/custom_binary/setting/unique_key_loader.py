"""キーの重複を許さない YAML の読み込み。"""

import yaml


class UniqueKeyLoader(yaml.SafeLoader):
    """安全なYAML読込に、キー重複と文字列以外のキーの拒否を加える。"""

    def construct_mapping(self, node, deep=False):
        result = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            if not isinstance(key, str):
                raise ValueError(f"YAMLのキーは文字列にしてください（{key_node.start_mark.line + 1}行）")
            if key in result:
                raise ValueError(f"YAMLのキーが重複しています: {key}（{key_node.start_mark.line + 1}行）")
            result[key] = self.construct_object(value_node, deep=deep)
        return result
