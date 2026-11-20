import re
from html import escape

import markdown2


class MathJaxMarkdown(markdown2.Markdown):
    _mathjax_inline = re.compile(
        r'(?<![\\~])~(?!~)(?:\\[^\n]|[^~\n])+?(?<!\\)~(?!~)'
        r'|(?<!\\)\\\((?:\\[^\n]|[^\\\n])*?\\\)',
    )

    def _do_code_spans(self, text):
        text = super()._do_code_spans(text)
        return self._mathjax_inline.sub(lambda match: self._hash_span(escape(match.group(0), quote=False)), text)
