import CodeBlock from "../Common/CodeBlock";

const toLines = (text) => (text || "").split("\n");

const CodeDiffView = ({ before = "", after = "", language = "javascript" }) => {
  const beforeLines = toLines(before);
  const afterLines = toLines(after);
  const max = Math.max(beforeLines.length, afterLines.length);

  return (
    <div className="space-y-3 rounded-lg border border-border bg-bg2 p-3">
      <p className="text-sm font-semibold text-text">Before / After Diff Preview</p>

      <div className="grid gap-3 lg:grid-cols-2">
        <div>
          <p className="mb-2 text-xs uppercase tracking-[0.08em] text-text2">Before</p>
          <CodeBlock code={before} language={language} />
        </div>
        <div>
          <p className="mb-2 text-xs uppercase tracking-[0.08em] text-text2">After</p>
          <CodeBlock code={after} language={language} />
        </div>
      </div>

      <div className="rounded-md border border-border bg-bg3 p-2">
        <p className="text-xs text-text2">Changed lines: {max}</p>
      </div>
    </div>
  );
};

export default CodeDiffView;
