'use client';

import { useState, useEffect } from 'react';
import ChatBox from '@/components/ChatBox';

export default function Home() {
  const [isLoaded, setIsLoaded] = useState(false);

  useEffect(() => {
    setIsLoaded(true);
  }, []);

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-6">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <h1 className="text-2xl font-bold text-gray-900">
                  {process.env.NEXT_PUBLIC_UNIVERSITY_NAME || 'University of Tasmania'}
                </h1>
              </div>
            </div>
            <div className="text-right">
              <p className="text-sm text-gray-600">
                {process.env.NEXT_PUBLIC_MODULE_CODE || 'UPP014'} S2 25 W6
              </p>
              <p className="text-lg font-semibold text-gray-900">
                {process.env.NEXT_PUBLIC_MODULE_NAME || 'Writing in Practice'}
              </p>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="bg-white rounded-lg shadow-lg p-8">
          {/* Module Introduction */}
          <div className="mb-8">
            <h2 className="text-3xl font-bold text-gray-900 mb-4">Welcome to Module 6</h2>

            <div className="bg-blue-50 border-l-4 border-blue-400 p-6 mb-6">
              <h3 className="text-lg font-semibold text-blue-900 mb-3">What you will learn:</h3>
              <ul className="list-disc list-inside text-blue-800 space-y-2">
                <li>The role of integrated sources in your writing</li>
                <li>How to integrate sources into academic writing</li>
                <li>How to apply APA style referencing for in-text citations</li>
                <li>How to establish an APA style reference list</li>
              </ul>
            </div>

            <div className="bg-green-50 border-l-4 border-green-400 p-6 mb-6">
              <h3 className="text-lg font-semibold text-green-900 mb-3">Learning Outcomes addressed:</h3>
              <ul className="list-disc list-inside text-green-800 space-y-2">
                <li><strong>ILO2:</strong> Communicate using academic conventions</li>
                <li><strong>ILO3:</strong> Evaluate and integrate academic sources</li>
              </ul>
            </div>

            <div className="bg-yellow-50 border-l-4 border-yellow-400 p-6 mb-8">
              <h3 className="text-lg font-semibold text-yellow-900 mb-3">Links to Assessment:</h3>
              <p className="text-yellow-800 mb-3">
                This module's content, readings, and discussion directly supports <strong>Assessment Task 2 (AT2): Writing Journal</strong>.
                The Writing Journal will consist of 3 paragraphs of writing.
              </p>
              <p className="text-yellow-800 mb-2">You will be assessed on the following criteria:</p>
              <ul className="list-disc list-inside text-yellow-800 space-y-1">
                <li>Use evidence to support analysis (ILO 3)</li>
                <li>Communicate with formal, academic language (ILO2)</li>
                <li>Acknowledge sources using academic referencing conventions (ILO 2, ILO3)</li>
              </ul>
            </div>

            <div className="bg-gray-50 p-6 rounded-lg mb-8">
              <p className="text-gray-700">
                If you are attending a workshop face to face or online, you will be discussing and completing
                discussion boards and writing drafts in class. If you are studying online, please work through
                these activities and post in MyLO to gain feedback.
              </p>
            </div>
          </div>

          {/* The Role of Sources */}
          <section className="mb-8">
            <h2 className="text-2xl font-bold text-gray-900 mb-4">The role of a source in your writing</h2>
            <div className="prose prose-lg text-gray-700 space-y-4">
              <p>
                Importantly, critically reading sources provides you with information on the topic you are studying,
                as well as the ability to form ideas and arguments in response to questions you are asked to answer
                in the form of essays or reports. Furthermore, to effectively incorporate a source into your paper,
                it is important to integrate it in such a manner that clarifies for your readers both the origin of
                the ideas and their contribution to your own analysis.
              </p>
              <p>
                Each source used should serve a deliberate purpose, and the reasoning behind its use should be apparent
                to the reader. Upon completing your draft, revisit your source integration to ensure each is used
                intentionally and its purpose is clear.
              </p>
              <p>
                The role of sources varies, serving as primary evidence, context, theoretical frameworks, or supporting
                arguments. Consider the role each source played in shaping your perspective on the topic as you draft
                your paragraphs. Whether providing context, evidence, counterarguments, or complicating your argument,
                sources should be utilised to support and enrich your analysis. Be aware that a single source may
                fulfill multiple roles within your purpose.
              </p>
            </div>
          </section>

          {/* Integrating Sources */}
          <section className="mb-8">
            <h2 className="text-2xl font-bold text-gray-900 mb-4">Integrating sources into writing</h2>
            <div className="prose prose-lg text-gray-700 space-y-4 mb-6">
              <p>
                Integrating a source is using another author's writing to establish or support your argument.
                Introducing another author's work can provide an authoritative voice, introduce a supportive or
                contrasting position, provide evidence for your own position or make a distinction between different
                authors' views (University of New South Wales, 2019).
              </p>
              <p className="font-semibold">There are four methods to integrate sources into your writing:</p>
            </div>

            {/* Four Methods Grid */}
            <div className="grid md:grid-cols-2 gap-6 mb-8">
              {/* Direct Quote */}
              <div className="bg-red-50 border border-red-200 rounded-lg p-6">
                <h3 className="text-xl font-bold text-red-900 mb-3">Direct Quote</h3>
                <p className="text-red-800 mb-4">
                  This is when you use the exact wording from another source. The wording must be identical
                  (Morley-Warner, 2009). You should be selective when using quotes, choose only a few lines
                  which emphasise or strongly support your point.
                </p>
                <div className="bg-red-100 p-4 rounded border-l-4 border-red-400">
                  <p className="text-red-800 text-sm">
                    <strong>Remember:</strong> Always include page numbers when citing a quotation and enclose
                    the quote in double quotation marks. Be sure to introduce the quote, quote it (with citation),
                    and then explain it afterward. We call this "sandwiching."
                  </p>
                </div>
              </div>

              {/* Paraphrase */}
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
                <h3 className="text-xl font-bold text-blue-900 mb-3">Paraphrase</h3>
                <p className="text-blue-800 mb-4">
                  This is when you convert a passage of another author's work into your own words (Morley-Warner, 2009).
                  It involves rephrasing the passage of text but not shortening it.
                </p>
                <div className="bg-blue-100 p-4 rounded border-l-4 border-blue-400">
                  <p className="text-blue-800 text-sm">
                    <strong>Useful when:</strong> A quotation would disrupt the flow or tone of your writing.
                  </p>
                </div>
              </div>

              {/* Summarise */}
              <div className="bg-green-50 border border-green-200 rounded-lg p-6">
                <h3 className="text-xl font-bold text-green-900 mb-3">Summarise</h3>
                <p className="text-green-800 mb-4">
                  This is when you filter a passage of another author's work into the essential points
                  (Morley-Warner, 2009). This is useful when you have several sources to include, or the
                  concept is large and needs drilling down to main points.
                </p>
                <div className="bg-green-100 p-4 rounded border-l-4 border-green-400">
                  <p className="text-green-800 text-sm">
                    <strong>Benefits:</strong> Helps you save word count and provides a broader overview of the source.
                  </p>
                </div>
              </div>

              {/* Synthesise */}
              <div className="bg-purple-50 border border-purple-200 rounded-lg p-6">
                <h3 className="text-xl font-bold text-purple-900 mb-3">Synthesise</h3>
                <p className="text-purple-800 mb-4">
                  A fourth method is synthesising which combines ideas from two or more sources to group or
                  chunk common ideas or positions on a topic.
                </p>
                <div className="bg-purple-100 p-4 rounded border-l-4 border-purple-400">
                  <p className="text-purple-800 text-sm">
                    <strong>Goal:</strong> As you move through UPP, aim to practice more synthesising than the
                    other three forms of source integration.
                  </p>
                </div>
              </div>
            </div>

            <div className="bg-orange-50 border-l-4 border-orange-400 p-6 rounded-lg">
              <p className="text-orange-800">
                <strong>Important:</strong> All forms need to be acknowledged with an in-text citation and a reference
                of the source in your reference list. Please refer to the APA Style Guide on the UTAS Library website
                for further assistance on how to cite and reference sources accurately.
              </p>
            </div>
          </section>
        </div>
      </main>

      {/* Chat Box Component */}
      <ChatBox />
    </div>
  );
}
