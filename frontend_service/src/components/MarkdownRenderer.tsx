'use client';

import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface MarkdownRendererProps {
  content: string;
  className?: string;
}

export default function MarkdownRenderer({ content, className = '' }: MarkdownRendererProps) {
  return (
    <div className={`prose prose-sm max-w-none ${className}`}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          // Customize heading styles
          h1: ({ children }) => (
            <h1 className="text-lg font-bold text-gray-900 mb-2 mt-4 first:mt-0">
              {children}
            </h1>
          ),
          h2: ({ children }) => (
            <h2 className="text-base font-semibold text-gray-800 mb-2 mt-3 first:mt-0">
              {children}
            </h2>
          ),
          h3: ({ children }) => (
            <h3 className="text-sm font-medium text-gray-700 mb-1 mt-2 first:mt-0">
              {children}
            </h3>
          ),
          
          // Customize paragraph styles
          p: ({ children }) => (
            <p className="text-sm text-gray-800 leading-relaxed mb-2 last:mb-0">
              {children}
            </p>
          ),
          
          // Customize list styles
          ul: ({ children }) => (
            <ul className="list-disc list-inside text-sm text-gray-800 mb-2 space-y-1">
              {children}
            </ul>
          ),
          ol: ({ children }) => (
            <ol className="list-decimal list-inside text-sm text-gray-800 mb-2 space-y-1">
              {children}
            </ol>
          ),
          li: ({ children }) => (
            <li className="text-sm text-gray-800">
              {children}
            </li>
          ),
          
          // Customize code styles
          code: ({ children, className }) => {
            const isInline = !className;
            if (isInline) {
              return (
                <code className="bg-gray-100 text-gray-800 px-1 py-0.5 rounded text-xs font-mono">
                  {children}
                </code>
              );
            }
            return (
              <code className="block bg-gray-100 text-gray-800 p-2 rounded text-xs font-mono overflow-x-auto">
                {children}
              </code>
            );
          },
          
          // Customize blockquote styles
          blockquote: ({ children }) => (
            <blockquote className="border-l-4 border-blue-200 pl-3 py-1 bg-blue-50 text-sm text-gray-700 italic mb-2">
              {children}
            </blockquote>
          ),
          
          // Customize link styles
          a: ({ children, href }) => (
            <a 
              href={href} 
              className="text-blue-600 hover:text-blue-800 underline text-sm"
              target="_blank"
              rel="noopener noreferrer"
            >
              {children}
            </a>
          ),
          
          // Customize table styles
          table: ({ children }) => (
            <div className="overflow-x-auto mb-2">
              <table className="min-w-full border border-gray-200 text-xs">
                {children}
              </table>
            </div>
          ),
          th: ({ children }) => (
            <th className="border border-gray-200 bg-gray-50 px-2 py-1 text-left font-medium text-gray-700">
              {children}
            </th>
          ),
          td: ({ children }) => (
            <td className="border border-gray-200 px-2 py-1 text-gray-800">
              {children}
            </td>
          ),
          
          // Customize strong/bold styles
          strong: ({ children }) => (
            <strong className="font-semibold text-gray-900">
              {children}
            </strong>
          ),
          
          // Customize emphasis/italic styles
          em: ({ children }) => (
            <em className="italic text-gray-700">
              {children}
            </em>
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
