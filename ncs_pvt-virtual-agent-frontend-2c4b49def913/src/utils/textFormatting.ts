/**
 * Utility functions for text formatting
 */

/**
 * Removes markdown-style formatting symbols from text
 * Currently handles:
 * - Bold/italic markers (**text**)
 * 
 * @param text The text to process
 * @returns Text with formatting symbols removed
 */
export function removeMarkdownFormatting(text: string): string {
  if (!text) return '';
  
  // Remove ** bold formatting
  return text.replace(/\*\*(.*?)\*\*/g, '$1');
} 