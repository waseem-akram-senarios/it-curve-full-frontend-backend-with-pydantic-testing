import { useWindowResize } from "@/hooks/useWindowResize";
import { useCallback, useEffect, useRef, useState } from "react";

type ChatMessageInput = {
  placeholder: string;
  accentColor: string;
  height: number;
  onSend?: (message: string) => void;
  inputTextColor?: string;
  disabled?: boolean;
  disabledText?: string;
};

export const ChatMessageInput = ({
  placeholder,
  accentColor,
  height,
  onSend,
  inputTextColor,
  disabled = false,
  disabledText = "Please wait while the agent is typing..."
}: ChatMessageInput) => {
  const [message, setMessage] = useState("");
  const [inputTextWidth, setInputTextWidth] = useState(0);
  const [inputWidth, setInputWidth] = useState(0);
  const hiddenInputRef = useRef<HTMLSpanElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const windowSize = useWindowResize();
  const [isTyping, setIsTyping] = useState(false);
  const [inputHasFocus, setInputHasFocus] = useState(false);
  const prevDisabledRef = useRef(disabled);

  const handleSend = useCallback(() => {
    if (!onSend || disabled) {
      return;
    }
    if (message === "") {
      return;
    }

    onSend(message);
    setMessage("");
  }, [onSend, message, disabled]);

  // Track typing state
  useEffect(() => {
    setIsTyping(true);
    const timeout = setTimeout(() => {
      setIsTyping(false);
    }, 500);

    return () => clearTimeout(timeout);
  }, [message]);

  // Update input text width measurement
  useEffect(() => {
    if (hiddenInputRef.current) {
      setInputTextWidth(hiddenInputRef.current.clientWidth);
    }
  }, [hiddenInputRef, message]);

  // Update input width on window resize
  useEffect(() => {
    if (inputRef.current) {
      setInputWidth(inputRef.current.clientWidth);
    }
  }, [hiddenInputRef, message, windowSize.width]);

  // Auto-focus input when it transitions from disabled to enabled
  useEffect(() => {
    // Only focus if transitioning from disabled to enabled
    if (prevDisabledRef.current && !disabled) {
      console.log("Input field re-enabled, auto-focusing");
      setTimeout(() => {
        inputRef.current?.focus();
      }, 100); // Small delay to ensure DOM is updated
    }
    prevDisabledRef.current = disabled;
  }, [disabled]);

  return (
    <div
      className="flex flex-col border-t border-t-gray-800"
      style={{ height: height }}
    >
      <div className="flex flex-row pt-3 gap-2 items-center relative">
        {disabled && (
          <div className="absolute -top-6 left-0 right-0 text-xs text-gray-500 text-center py-1 italic bg-gray-100 rounded z-10">
            {disabledText}
          </div>
        )}
        <div
          className={`w-2 h-4 bg-${inputHasFocus ? accentColor : "gray"}-${
            inputHasFocus ? 500 : 800
          } ${inputHasFocus ? "shadow-" + accentColor : ""} absolute left-2 ${
            !isTyping && inputHasFocus ? "cursor-animation" : ""
          }`}
          style={{
            transform:
              "translateX(" +
              (message.length > 0
                ? Math.min(inputTextWidth, inputWidth - 20) - 4
                : 0) +
              "px)",
          }}
        ></div>
        <input
          ref={inputRef}
          className={`w-full text-xs caret-transparent bg-transparent ${disabled ? 'opacity-50 cursor-not-allowed' : 'opacity-25'} p-2 pr-6 rounded-sm focus:opacity-100 focus:outline-none focus:border-${accentColor}-700 focus:ring-1 focus:ring-${accentColor}-700 text-black`}
          style={{
            paddingLeft: message.length > 0 ? "12px" : "24px",
            caretShape: "block",
            color: inputTextColor || "white",
          }}
          placeholder={disabled ? "Message input disabled" : placeholder}
          value={message}
          onChange={(e) => {
            if (!disabled) {
              setMessage(e.target.value);
            }
          }}
          onFocus={() => {
            if (!disabled) {
              setInputHasFocus(true);
            }
          }}
          onBlur={() => {
            setInputHasFocus(false);
          }}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !disabled) {
              handleSend();
            }
          }}
          disabled={disabled}
        ></input>
        <span
          ref={hiddenInputRef}
          className="absolute top-0 left-0 text-xs pl-3 text-black pointer-events-none opacity-0"
        >
          {message.replaceAll(" ", "\u00a0")}
        </span>
        <button
          disabled={message.length === 0 || !onSend || disabled}
          onClick={handleSend}
          className={`text-xs uppercase text-${accentColor}-500 hover:bg-${accentColor}-950 p-2 rounded-md opacity-${
            message.length > 0 && !disabled ? 100 : 25
          } pointer-events-${message.length > 0 && !disabled ? "auto" : "none"}`}
        >
          Send
        </button>
      </div>
    </div>
  );
};
