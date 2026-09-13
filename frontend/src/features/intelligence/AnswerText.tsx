import type { ReactNode } from 'react'

/**
 * The answer as the agent wrote it: a small, deliberate subset of markdown — bold,
 * inline code, bullets, numbered lists and one level of heading.
 *
 * No library and no `dangerouslySetInnerHTML`. The text comes from a model, so it is
 * never turned into markup; it is parsed into React nodes and anything unrecognised
 * stays literal. Links are deliberately not rendered — a URL in an answer would be the
 * model's, and every real one is on the evidence below it.
 */
export function AnswerText({ text }: { text: string }) {
  return <div className="space-y-2.5 text-sm leading-relaxed text-ink">{blocks(text)}</div>
}

function blocks(text: string): ReactNode[] {
  const out: ReactNode[] = []
  const lines = text.split('\n')
  let index = 0

  while (index < lines.length) {
    const line = lines[index]

    if (!line.trim()) {
      index++
      continue
    }

    const heading = line.match(/^#{1,6}\s+(.*)$/)
    if (heading) {
      out.push(
        <h3 key={index} className="pt-1 text-sm font-semibold text-ink">
          {inline(heading[1])}
        </h3>,
      )
      index++
      continue
    }

    // A run of consecutive list items of the same kind becomes one list.
    const ordered = isOrdered(line)
    if (ordered !== null) {
      const items: string[] = []
      while (index < lines.length && isOrdered(lines[index]) === ordered) {
        items.push(lines[index].replace(ordered ? /^\s*\d+[.)]\s+/ : /^\s*[-*•]\s+/, ''))
        index++
      }
      out.push(list(index, ordered, items))
      continue
    }

    // Everything else is a paragraph: consecutive plain lines, joined.
    const paragraph: string[] = []
    while (index < lines.length && lines[index].trim() && isOrdered(lines[index]) === null) {
      if (/^#{1,6}\s+/.test(lines[index])) break
      paragraph.push(lines[index].trim())
      index++
    }
    out.push(<p key={index}>{inline(paragraph.join(' '))}</p>)
  }

  return out
}

/** `true` for `1.`, `false` for `-`, `null` for anything that is not a list item. */
function isOrdered(line: string): boolean | null {
  if (/^\s*\d+[.)]\s+/.test(line)) return true
  if (/^\s*[-*•]\s+/.test(line)) return false
  return null
}

function list(key: number, ordered: boolean, items: string[]): ReactNode {
  const children = items.map((item, position) => (
    <li key={position} className="pl-1 marker:text-faint">
      {inline(item)}
    </li>
  ))
  return ordered ? (
    <ol key={key} className="list-decimal space-y-1.5 pl-5">
      {children}
    </ol>
  ) : (
    <ul key={key} className="list-disc space-y-1.5 pl-5">
      {children}
    </ul>
  )
}

/** `**bold**` and `` `code` ``. An unmatched marker stays the character it is. */
function inline(text: string): ReactNode[] {
  return text.split(/(\*\*[^*]+\*\*|`[^`]+`)/g).map((part, index) => {
    if (part.startsWith('**') && part.endsWith('**') && part.length > 4) {
      return (
        <strong key={index} className="font-semibold">
          {part.slice(2, -2)}
        </strong>
      )
    }
    if (part.startsWith('`') && part.endsWith('`') && part.length > 2) {
      return (
        <code
          key={index}
          className="rounded border border-line bg-surface px-1 py-0.5 font-mono text-[0.8125rem]"
        >
          {part.slice(1, -1)}
        </code>
      )
    }
    return part
  })
}
