import { formatAssistantResponse } from '../../lib/chatFormatter'

export default function MessageBubble({ role, text }) {
  const isUser = role === 'user'
  const displayText = isUser ? text : formatAssistantResponse(text)
  return (
    <div className={`mb-3 flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-[82%] rounded-2xl px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap shadow-[0_1px_0_rgba(15,23,42,0.03)] ${
          isUser
            ? 'bg-(--brand) text-white rounded-br-sm'
            : 'bg-(--surface-soft) border border-(--border) rounded-bl-sm text-(--text)'
        }`}
      >
        {displayText}
      </div>
    </div>
  )
}

