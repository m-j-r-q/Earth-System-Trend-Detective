import { useEffect, useState } from 'react'
import { fillTemplate } from '../lib/format'

/** Floating step-by-step guide. Highlights the part of the page each step talks about. */
export default function DemoGuide({ demo, step, goStep, ctx, busy, onExit }) {
  const [hist, setHist] = useState({})
  const s = demo.steps[step]
  const last = step === demo.steps.length - 1

  // Remember what each step showed, so the next step can say "before it was ...".
  useEffect(() => {
    if (ctx) setHist((h) => ({ ...h, [step]: ctx }))
  }, [ctx, step])

  useEffect(() => {
    const clear = () => document.querySelectorAll('.tour-highlight').forEach((n) => n.classList.remove('tour-highlight'))
    clear()
    if (s.target) {
      const node = document.querySelector(`[data-tour="${s.target}"]`)
      if (node) {
        node.classList.add('tour-highlight')
        node.scrollIntoView({ block: 'nearest', behavior: 'smooth' })
      }
    }
    return clear
  }, [step, ctx, s.target])

  const text = ctx ? fillTemplate(s.text, { ...ctx, prev: hist[step - 1] ?? {} }) : 'Loading the data…'

  return (
    <aside className="guide" aria-live="polite">
      <p className="meta">
        {demo.title} · step {step + 1} of {demo.steps.length}
      </p>
      <h3>{s.title}</h3>
      <p className={`prose ${busy ? 'stale' : ''}`}>{text}</p>
      <div className="guidebar">
        <button className="link" onClick={onExit}>Leave demo</button>
        <span>
          <button disabled={step === 0} onClick={() => goStep(step - 1)}>Back</button>
          {last ? (
            <button className="primary" onClick={onExit}>Finish</button>
          ) : (
            <button className="primary" onClick={() => goStep(step + 1)}>Next</button>
          )}
        </span>
      </div>
    </aside>
  )
}
