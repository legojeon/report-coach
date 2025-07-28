import React, { useState, useEffect } from 'react';
import { useEditor, EditorContent, useEditorState } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import { TextStyle } from '@tiptap/extension-text-style';  // named import 사용
import FontSize from '@tiptap/extension-font-size';
import TextAlign from '@tiptap/extension-text-align';
import './TiptapEditor.css';

const extensions = [
  StarterKit,
  TextStyle,  // named import
  FontSize,
  TextAlign.configure({
    types: ['heading', 'paragraph', 'bulletList', 'orderedList'],
  }),
];

function MenuBar({ editor }) {
  const [currentLineHeight, setCurrentLineHeight] = useState('1.5');

  const editorState = useEditorState({
    editor,
    selector: ctx => {
      return {
        isBold: ctx.editor.isActive('bold'),
        canBold: ctx.editor.can().chain().focus().toggleBold().run(),
        isItalic: ctx.editor.isActive('italic'),
        canItalic: ctx.editor.can().chain().focus().toggleItalic().run(),
        isStrike: ctx.editor.isActive('strike'),
        canStrike: ctx.editor.can().chain().focus().toggleStrike().run(),
        isCode: ctx.editor.isActive('code'),
        canCode: ctx.editor.can().chain().focus().toggleCode().run(),
        isParagraph: ctx.editor.isActive('paragraph'),
        isHeading1: ctx.editor.isActive('heading', { level: 1 }),
        isHeading2: ctx.editor.isActive('heading', { level: 2 }),
        isHeading3: ctx.editor.isActive('heading', { level: 3 }),
        isBulletList: ctx.editor.isActive('bulletList'),
        isOrderedList: ctx.editor.isActive('orderedList'),
        isCodeBlock: ctx.editor.isActive('codeBlock'),
        isBlockquote: ctx.editor.isActive('blockquote'),
        isAlignLeft: ctx.editor.isActive({ textAlign: 'left' }),
        isAlignCenter: ctx.editor.isActive({ textAlign: 'center' }),
        isAlignRight: ctx.editor.isActive({ textAlign: 'right' }),
        isAlignJustify: ctx.editor.isActive({ textAlign: 'justify' }),
        canUndo: ctx.editor.can().chain().focus().undo().run(),
        canRedo: ctx.editor.can().chain().focus().redo().run(),
      }
    },
  });

  const setLineHeight = (lineHeight) => {
    setCurrentLineHeight(lineHeight);
    
    // 에디터 컨테이너에 클래스 적용
    const editorElement = editor.view.dom.closest('.tiptap');
    if (editorElement) {
      // 기존 줄간격 클래스 제거
      editorElement.classList.remove('line-height-115', 'line-height-15', 'line-height-2');
      // 새로운 줄간격 클래스 추가
      if (lineHeight === '1.15') {
        editorElement.classList.add('line-height-115');
      } else if (lineHeight === '1.5') {
        editorElement.classList.add('line-height-15');
      } else if (lineHeight === '2') {
        editorElement.classList.add('line-height-2');
      }
    }
  };

  return (
    <div className="border-b border-gray-200 p-2 bg-gray-50">
      <div className="flex flex-wrap gap-1">
        <button
          onClick={() => editor.chain().focus().toggleBold().run()}
          disabled={!editorState.canBold}
          className={`px-2 py-1 rounded text-sm font-medium ${
            editorState.isBold ? 'bg-primary-600 text-white' : 'bg-white text-gray-700 hover:bg-gray-100'
          }`}
        >
          Bold
        </button>
        <button
          onClick={() => editor.chain().focus().toggleItalic().run()}
          disabled={!editorState.canItalic}
          className={`px-2 py-1 rounded text-sm font-medium ${
            editorState.isItalic ? 'bg-primary-600 text-white' : 'bg-white text-gray-700 hover:bg-gray-100'
          }`}
        >
          Italic
        </button>
        <button
          onClick={() => editor.chain().focus().toggleStrike().run()}
          disabled={!editorState.canStrike}
          className={`px-2 py-1 rounded text-sm font-medium ${
            editorState.isStrike ? 'bg-primary-600 text-white' : 'bg-white text-gray-700 hover:bg-gray-100'
          }`}
        >
          Strike
        </button>
        <button
          onClick={() => editor.chain().focus().toggleCode().run()}
          disabled={!editorState.canCode}
          className={`px-2 py-1 rounded text-sm font-medium ${
            editorState.isCode ? 'bg-primary-600 text-white' : 'bg-white text-gray-700 hover:bg-gray-100'
          }`}
        >
          Code
        </button>
        <div className="w-px h-6 bg-gray-300 mx-1"></div>
        <button
          onClick={() => editor.chain().focus().setParagraph().run()}
          className={`px-2 py-1 rounded text-sm font-medium ${
            editorState.isParagraph ? 'bg-primary-600 text-white' : 'bg-white text-gray-700 hover:bg-gray-100'
          }`}
        >
          P
        </button>
        <button
          onClick={() => editor.chain().focus().toggleHeading({ level: 1 }).run()}
          className={`px-2 py-1 rounded text-sm font-medium ${
            editorState.isHeading1 ? 'bg-primary-600 text-white' : 'bg-white text-gray-700 hover:bg-gray-100'
          }`}
        >
          H1
        </button>
        <button
          onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()}
          className={`px-2 py-1 rounded text-sm font-medium ${
            editorState.isHeading2 ? 'bg-primary-600 text-white' : 'bg-white text-gray-700 hover:bg-gray-100'
          }`}
        >
          H2
        </button>
        <button
          onClick={() => editor.chain().focus().toggleHeading({ level: 3 }).run()}
          className={`px-2 py-1 rounded text-sm font-medium ${
            editorState.isHeading3 ? 'bg-primary-600 text-white' : 'bg-white text-gray-700 hover:bg-gray-100'
          }`}
        >
          H3
        </button>
        <div className="w-px h-6 bg-gray-300 mx-1"></div>
        <button
          onClick={() => editor.chain().focus().toggleBulletList().run()}
          className={`px-2 py-1 rounded text-sm font-medium ${
            editorState.isBulletList ? 'bg-primary-600 text-white' : 'bg-white text-gray-700 hover:bg-gray-100'
          }`}
        >
          List
        </button>
        <button
          onClick={() => editor.chain().focus().toggleOrderedList().run()}
          className={`px-2 py-1 rounded text-sm font-medium ${
            editorState.isOrderedList ? 'bg-primary-600 text-white' : 'bg-white text-gray-700 hover:bg-gray-100'
          }`}
        >
          OL
        </button>
        <button
          onClick={() => editor.chain().focus().toggleCodeBlock().run()}
          className={`px-2 py-1 rounded text-sm font-medium ${
            editorState.isCodeBlock ? 'bg-primary-600 text-white' : 'bg-white text-gray-700 hover:bg-gray-100'
          }`}
        >
          Code Block
        </button>
        <button
          onClick={() => editor.chain().focus().toggleBlockquote().run()}
          className={`px-2 py-1 rounded text-sm font-medium ${
            editorState.isBlockquote ? 'bg-primary-600 text-white' : 'bg-white text-gray-700 hover:bg-gray-100'
          }`}
        >
          Quote
        </button>
        <div className="w-px h-6 bg-gray-300 mx-1"></div>
        <button
          onClick={() => editor.chain().focus().undo().run()}
          disabled={!editorState.canUndo}
          className="px-2 py-1 rounded text-sm font-medium bg-white text-gray-700 hover:bg-gray-100 disabled:opacity-50"
        >
          Undo
        </button>
        <button
          onClick={() => editor.chain().focus().redo().run()}
          disabled={!editorState.canRedo}
          className="px-2 py-1 rounded text-sm font-medium bg-white text-gray-700 hover:bg-gray-100 disabled:opacity-50"
        >
          Redo
        </button>
        <div className="w-px h-6 bg-gray-300 mx-1"></div>
        <button
          onClick={() => editor.chain().focus().setTextAlign('left').run()}
          className={`px-2 py-1 rounded text-sm font-medium ${
            editorState.isAlignLeft ? 'bg-primary-600 text-white' : 'bg-white text-gray-700 hover:bg-gray-100'
          }`}
        >
          Left
        </button>
        <button
          onClick={() => editor.chain().focus().setTextAlign('center').run()}
          className={`px-2 py-1 rounded text-sm font-medium ${
            editorState.isAlignCenter ? 'bg-primary-600 text-white' : 'bg-white text-gray-700 hover:bg-gray-100'
          }`}
        >
          Center
        </button>
        <button
          onClick={() => editor.chain().focus().setTextAlign('right').run()}
          className={`px-2 py-1 rounded text-sm font-medium ${
            editorState.isAlignRight ? 'bg-primary-600 text-white' : 'bg-white text-gray-700 hover:bg-gray-100'
          }`}
        >
          Right
        </button>
        <button
          onClick={() => editor.chain().focus().setTextAlign('justify').run()}
          className={`px-2 py-1 rounded text-sm font-medium ${
            editorState.isAlignJustify ? 'bg-primary-600 text-white' : 'bg-white text-gray-700 hover:bg-gray-100'
          }`}
        >
          Justify
        </button>
        <div className="w-px h-6 bg-gray-300 mx-1"></div>
        <select
          onChange={(e) => editor.chain().focus().setFontSize(e.target.value).run()}
          className="px-2 py-1 rounded text-sm font-medium bg-white text-gray-700 border border-gray-300"
        >
          <option value="12px">12px</option>
          <option value="14px">14px</option>
          <option value="16px">16px</option>
          <option value="18px">18px</option>
          <option value="20px">20px</option>
          <option value="24px">24px</option>
          <option value="28px">28px</option>
          <option value="32px">32px</option>
        </select>
        <select
          value={currentLineHeight}
          onChange={(e) => setLineHeight(e.target.value)}
          className="px-2 py-1 rounded text-sm font-medium bg-white text-gray-700 border border-gray-300"
        >
          <option value="1.15">1.15</option>
          <option value="1.5">1.5</option>
          <option value="2">2</option>
        </select>
      </div>
    </div>
  );
}

const TiptapEditor = ({ content, onChange }) => {
  const editor = useEditor({
    extensions,
    content: content || `
<h2>보고서 작성</h2>
<p>
  ai 탐구코치와 보고서를 작성하세요. 다양한 서식을 사용할 수 있습니다.
</p>
<ul>
  <li>목차</li>
  <li>서론</li>
  <li>본론</li>
  <li>결론</li>
  <li>참고문헌</li>
</ul>
<p>위 양식을 활용하면 정돈된 글을 쓸 수 있어요</p>
`,
    onUpdate: ({ editor }) => {
      onChange(editor.getHTML());
    },
  });

  // content가 변경될 때 에디터 내용 업데이트
  useEffect(() => {
    if (editor && content && content !== editor.getHTML()) {
      editor.commands.setContent(content);
    }
  }, [editor, content]);

  if (!editor) {
    return null;
  }

  return (
    <div className="flex flex-col h-full">
      <MenuBar editor={editor} />
      <div className="flex-1 overflow-y-auto">
        <EditorContent 
          editor={editor} 
          className="p-8 text-lg leading-relaxed text-gray-900 min-h-full focus:outline-none"
        />
      </div>
    </div>
  );
};

export default TiptapEditor; 