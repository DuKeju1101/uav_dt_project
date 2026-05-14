# LaTeX 编译说明

如果 PDF 中没有正文引用标识，也没有 `References` 章节，通常是 BibTeX 没有成功运行。本文使用 Wiley 模板类 `USG.cls`，该模板会自动设置参考文献样式：

```tex
\bibliographystyle{wileyNJD-Chicago}
```

因此编译时需要保证 `paper/wileyNJD-Chicago.bst` 和 `paper/refs.bib` 都能被 BibTeX 找到。

## Overleaf 推荐步骤

1. 将 `paper/` 目录作为论文工程上传到 Overleaf，或确保 Overleaf 的主文件设置为 `paper/main.tex`。
2. 在 Overleaf 左上角 `Menu` 中确认 Compiler 为 `pdfLaTeX`。
3. 点击 `Recompile from scratch`，不要只普通重编译一次。
4. 如果仍然没有参考文献，打开 Logs，搜索 `BibTeX`、`I couldn't open style file`、`Citation ... undefined`。

## 本地编译顺序

在 `paper/` 目录下执行：

```bash
pdflatex main.tex
bibtex main
pdflatex main.tex
pdflatex main.tex
```

如果使用 `latexmk`：

```bash
latexmk -pdf main.tex
```

## 常见错误

- 只运行一次 `pdflatex`：会导致没有参考文献或引用显示异常。
- 缺少 `wileyNJD-Chicago.bst`：BibTeX 找不到 Wiley 模板参考文献样式。
- 编译了模板示例文件 `Optimal-Design-layout.tex`，而不是本文主文件 `main.tex`。
- Overleaf 主文件没有设置为 `main.tex`。
