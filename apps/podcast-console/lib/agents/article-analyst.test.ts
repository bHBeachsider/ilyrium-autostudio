import { describe, expect, it } from "vitest"
import { htmlToText } from "./article-analyst"

describe("htmlToText", () => {
  it("strips scripts, styles, chrome and tags but keeps article text", () => {
    const html = `<html><head><style>.x{color:red}</style><script>var a=1;</script></head>
      <body><nav><a href="/">Home</a></nav>
      <article><h1>Council approves tower</h1>
      <p>The council voted 4&#8211;1 to approve the &quot;Main Street&quot; project&nbsp;on Tuesday.</p>
      <p>Construction starts in <b>March</b>.</p></article>
      <footer>© 2026 Paper</footer></body></html>`
    const text = htmlToText(html)
    expect(text).toContain("Council approves tower")
    expect(text).toContain('voted 4–1 to approve the "Main Street" project on Tuesday')
    expect(text).toContain("Construction starts in March")
    expect(text).not.toContain("color:red")
    expect(text).not.toContain("var a=1")
    expect(text).not.toContain("Home")
  })
  it("collapses whitespace and blank lines", () => {
    expect(htmlToText("<p>a</p>\n\n\n<p>   b   c</p>")).toBe("a\nb c")
  })
})
