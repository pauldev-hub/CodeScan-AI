import Prism from "prismjs";
import "prismjs/components/prism-python";
import "prismjs/components/prism-javascript";
import "prismjs/components/prism-jsx";
import "prismjs/components/prism-json";
import "prismjs/components/prism-markup";

import { useMemo } from "react";

import CopyButton from "./CopyButton";

const CodeBlock = ({ code = "", language = "javascript" }) => {
  const safeLanguage = Prism.languages[language] ? language : "javascript";

  const highlighted = useMemo(
    () => Prism.highlight(code, Prism.languages[safeLanguage], safeLanguage),
    [code, safeLanguage]
  );

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-xs text-text2">
        <span className="font-mono uppercase">{safeLanguage}</span>
        <CopyButton value={code} />
      </div>
      <pre className="codescan-prism">
        <code className={`language-${safeLanguage}`} dangerouslySetInnerHTML={{ __html: highlighted }} />
      </pre>
    </div>
  );
};

export default CodeBlock;
