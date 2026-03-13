import Markdown from "react-markdown";
import type { Message } from "../types";
import SourcePanel from "./SourcePanel";

interface MessageBubbleProps {
  message: Message;
}

export default function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[80%] rounded-2xl px-4 py-3 ${
          isUser
            ? "bg-indigo-600 text-white"
            : "bg-white text-slate-800 border border-slate-200 shadow-sm"
        }`}
      >
        {isUser ? (
          <div className="text-sm whitespace-pre-wrap">{message.content}</div>
        ) : (
          <div className="prose prose-sm prose-slate max-w-none [&>*:first-child]:mt-0 [&>*:last-child]:mb-0">
            <Markdown>{message.content}</Markdown>
          </div>
        )}

        {!isUser && message.confidence === "low" && (
          <span className="mt-1 inline-block rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-medium text-amber-700">
            Low confidence
          </span>
        )}

        {!isUser && message.sources && (
          <SourcePanel sources={message.sources} />
        )}
      </div>
    </div>
  );
}
