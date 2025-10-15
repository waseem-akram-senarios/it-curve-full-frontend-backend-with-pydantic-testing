import React from "react";
import { removeMarkdownFormatting } from "@/utils/textFormatting";

type ChatMessageProps = {
  message: string;
  accentColor: string;
  name: string;
  isSelf: boolean;
  hideName?: boolean;
};

export const ChatMessage = ({
  name,
  message,
  accentColor,
  isSelf,
  hideName,
}: ChatMessageProps) => {
  // Determine if this is an agent message (not self)
  const isAgent = !isSelf;
  
  // Remove markdown formatting from agent messages
  const processedMessage = isAgent ? removeMarkdownFormatting(message) : message;

  return (
    <div
      className={`flex flex-col gap-1 mb-2 ${
        isSelf ? "items-end" : "items-start"
      } ${hideName ? "pt-0" : "pt-4"}`}
    >
      {/* Agent avatar */}
      {!hideName && isAgent && (
        <div className="mb-1 flex items-center justify-center w-10 h-10">
          <div className="w-9 h-9 rounded-full border border-gray-300 shadow-sm bg-[#e0e0e0] flex items-center justify-center overflow-hidden">
            <img
              src="Sphere-Gif-2-unscreen.gif"
              alt="Agent"
              className="w-full h-full object-cover object-top"
            />
          </div>
        </div>
      )}
      {/* User label (optional) */}
      {/* {!hideName && isSelf && (
        <div className="text-gray-400 uppercase text-xs font-bold mb-1 tracking-wide">YOU</div>
      )} */}
      <div
        className={`rounded-lg px-4 py-3 max-w-[80%] break-words shadow-md border ${
          isSelf
            ? `bg-${accentColor}-600 text-white border-transparent self-end`
            : `bg-[mintcream] text-black border-gray-200 self-start`
        }`}
      >
        {processedMessage}
      </div>
    </div>
  );
};
