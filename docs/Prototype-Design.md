# XU-News-AI-RAG: Prototype Design Document
## User Interface & User Experience Specifications

---

## 1. Design System & Visual Guidelines

### 1.1 Color Palette
```css
/* Primary Colors */
--primary-blue: #1976D2
--primary-blue-dark: #1565C0
--primary-blue-light: #42A5F5

/* Secondary Colors */
--secondary-green: #388E3C
--secondary-orange: #F57C00
--secondary-purple: #7B1FA2

/* Neutral Colors */
--gray-900: #212121  /* Dark text */
--gray-700: #424242  /* Medium text */
--gray-500: #9E9E9E  /* Light text */
--gray-300: #E0E0E0  /* Borders */
--gray-100: #F5F5F5  /* Background */
--white: #FFFFFF
--black: #000000

/* Semantic Colors */
--success: #4CAF50
--warning: #FF9800
--error: #F44336
--info: #2196F3
```

### 1.2 Typography
```css
/* Font Family */
--font-primary: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif
--font-mono: 'JetBrains Mono', 'Courier New', monospace

/* Font Sizes */
--text-xs: 12px
--text-sm: 14px
--text-base: 16px
--text-lg: 18px
--text-xl: 20px
--text-2xl: 24px
--text-3xl: 30px
--text-4xl: 36px

/* Font Weights */
--font-light: 300
--font-normal: 400
--font-medium: 500
--font-semibold: 600
--font-bold: 700
```

### 1.3 Spacing & Layout
```css
/* Spacing Scale */
--space-1: 4px
--space-2: 8px
--space-3: 12px
--space-4: 16px
--space-5: 20px
--space-6: 24px
--space-8: 32px
--space-10: 40px
--space-12: 48px
--space-16: 64px

/* Border Radius */
--radius-sm: 4px
--radius-md: 8px
--radius-lg: 12px
--radius-xl: 16px
--radius-full: 9999px

/* Shadows */
--shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.05)
--shadow-md: 0 4px 6px rgba(0, 0, 0, 0.1)
--shadow-lg: 0 10px 15px rgba(0, 0, 0, 0.1)
--shadow-xl: 0 20px 25px rgba(0, 0, 0, 0.15)
```

---

## 2. Application Layout Structure

### 2.1 Overall Application Layout
```
┌─────────────────────────────────────────────────────────────────┐
│                          Header                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │    Logo      │  │  Navigation  │  │ User Profile │        │
│  └──────────────┘  └──────────────┘  └──────────────┘        │
├─────────────────────────────────────────────────────────────────┤
│ ┌──────────┐ │                                               │ │
│ │          │ │                                               │ │
│ │          │ │                 Main Content                  │ │
│ │ Sidebar  │ │                    Area                       │ │
│ │          │ │                                               │ │
│ │          │ │                                               │ │
│ └──────────┘ │                                               │ │
├─────────────────────────────────────────────────────────────────┤
│                          Footer                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Responsive Breakpoints
```css
/* Mobile First Approach */
--breakpoint-sm: 640px   /* Small devices (phones) */
--breakpoint-md: 768px   /* Medium devices (tablets) */
--breakpoint-lg: 1024px  /* Large devices (desktops) */
--breakpoint-xl: 1280px  /* Extra large devices */

/* Mobile Layout: Stack sidebar below header */
/* Tablet Layout: Collapsible sidebar */
/* Desktop Layout: Full sidebar + main content */
```

---

## 3. Page-by-Page Interface Design

### 3.1 Login/Registration Page

#### 3.1.1 Login Interface Wireframe
```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│                         XU-News AI-RAG                         │
│                     Knowledge Base System                       │
│                                                                 │
│               ┌─────────────────────────────────┐               │
│               │                                 │               │
│               │            LOGIN                │               │
│               │                                 │               │
│               │  ┌───────────────────────────┐  │               │
│               │  │ Username                  │  │               │
│               │  │ [____________________]    │  │               │
│               │  └───────────────────────────┘  │               │
│               │                                 │               │
│               │  ┌───────────────────────────┐  │               │
│               │  │ Password                  │  │               │
│               │  │ [____________________]    │  │               │
│               │  └───────────────────────────┘  │               │
│               │                                 │               │
│               │  ☐ Remember me                  │               │
│               │                                 │               │
│               │  [    LOGIN    ]               │               │
│               │                                 │               │
│               │  Don't have an account?         │               │
│               │  <Sign up here>                 │               │
│               │                                 │               │
│               └─────────────────────────────────┘               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### 3.1.2 Registration Interface
```
┌─────────────────────────────────────────────────────────────────┐
│                        CREATE ACCOUNT                           │
│                                                                 │
│               ┌─────────────────────────────────┐               │
│               │  ┌───────────────────────────┐  │               │
│               │  │ Username                  │  │               │
│               │  │ [____________________]    │  │               │
│               │  └───────────────────────────┘  │               │
│               │                                 │               │
│               │  ┌───────────────────────────┐  │               │
│               │  │ Email Address             │  │               │
│               │  │ [____________________]    │  │               │
│               │  └───────────────────────────┘  │               │
│               │                                 │               │
│               │  ┌───────────────────────────┐  │               │
│               │  │ Password                  │  │               │
│               │  │ [____________________]    │  │               │
│               │  └───────────────────────────┘  │               │
│               │                                 │               │
│               │  ┌───────────────────────────┐  │               │
│               │  │ Confirm Password          │  │               │
│               │  │ [____________________]    │  │               │
│               │  └───────────────────────────┘  │               │
│               │                                 │               │
│               │  ☐ I agree to Terms & Privacy  │               │
│               │                                 │               │
│               │  [   CREATE ACCOUNT   ]        │               │
│               │                                 │               │
│               └─────────────────────────────────┘               │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 Dashboard/Home Page

#### 3.2.1 Dashboard Layout
```
┌─────────────────────────────────────────────────────────────────┐
│ Logo  Dashboard  Search  Content  Analytics    👤 John Doe ▼   │
├─────────────────────────────────────────────────────────────────┤
│ ┌─────────┐ │ ┌─────────────────────────────────────────────┐ │
│ │ 📊 Stats│ │ │              Quick Search                   │ │
│ │         │ │ │ ┌─────────────────────────────────────────┐ │ │
│ │ 📄 1,234│ │ │ │ What would you like to find today?     │ │ │
│ │ Docs    │ │ │ │ [_________________________________] [🔍] │ │ │
│ │         │ │ │ └─────────────────────────────────────────┘ │ │
│ │ 🔍 567  │ │ ├─────────────────────────────────────────────┤ │
│ │ Searches│ │ │           Recent Activity                   │ │
│ │         │ │ │                                             │ │
│ │ 📈 15   │ │ │ • New articles from Tech News (5 min ago) │ │
│ │ Sources │ │ │ • Search: "AI developments" (1 hour ago)  │ │
│ │         │ │ │ • Upload: "Research Paper.pdf" (2h ago)   │ │
│ ├─────────┤ │ │ • 15 new articles from RSS feeds (3h ago)  │ │
│ │ 🏷️ Tags │ │ ├─────────────────────────────────────────────┤ │
│ │         │ │ │           Trending Keywords                 │ │
│ │ AI       │ │ │                                             │ │
│ │ Tech     │ │ │ 🔥 Artificial Intelligence    (45 docs)    │ │
│ │ Research │ │ │ 📈 Machine Learning         (32 docs)    │ │
│ │ News     │ │ │ 🚀 Startup Funding          (28 docs)    │ │
│ │ Industry │ │ │ 🏢 Technology Companies     (24 docs)    │ │
│ │         │ │ │ 💰 Investment Trends        (21 docs)    │ │
│ └─────────┘ │ └─────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

#### 3.2.2 Sidebar Navigation
```
┌─────────────┐
│ 🏠 Dashboard│
│ 🔍 Search   │
│ 📄 Documents│
│ 📊 Analytics│
│ ⚙️ Sources  │
│ 📧 Alerts   │
│ ⚙️ Settings │
│             │
│ ─────────── │
│             │
│ 📂 Folders  │
│ > Research  │
│ > Tech News │
│ > Reports   │
│             │
│ ─────────── │
│             │
│ 🏷️ Quick Tags│
│ # ai        │
│ # tech      │
│ # startup   │
│ # research  │
│ + Add Tag   │
└─────────────┘
```

### 3.3 Search Interface

#### 3.3.1 Search Page Layout
```
┌─────────────────────────────────────────────────────────────────┐
│ Header with Navigation                                          │
├─────────────────────────────────────────────────────────────────┤
│ ┌─────────┐ │ ┌─────────────────────────────────────────────┐ │
│ │Filters  │ │ │            Search Interface                 │ │
│ │         │ │ │                                             │ │
│ │📅 Date  │ │ │ ┌─────────────────────────────────────────┐ │ │
│ │From:    │ │ │ │ Search knowledge base...                │ │ │
│ │[______] │ │ │ │ [_________________________________] [🔍] │ │ │
│ │To:      │ │ │ └─────────────────────────────────────────┘ │ │
│ │[______] │ │ │                                             │ │
│ │         │ │ │ Recent: "AI trends" "startup news" "tech"   │ │
│ │📂 Source│ │ │                                             │ │
│ │☐ RSS    │ │ ├─────────────────────────────────────────────┤ │
│ │☐ Upload │ │ │              Search Results                  │ │
│ │☐ Web    │ │ │                                             │ │
│ │         │ │ │ 🔍 Found 24 results for "artificial intel.."│ │
│ │🏷️ Tags  │ │ │                                             │ │
│ │☐ ai     │ │ │ ┌─────────────────────────────────────────┐ │ │
│ │☐ tech   │ │ │ │ ⭐ 95% AI Revolution in Healthcare       │ │ │
│ │☐ news   │ │ │ │ 📅 2 hours ago • 📰 TechNews.com        │ │ │
│ │☐ research│ │ │ │ Latest developments in AI-powered...    │ │ │
│ │         │ │ │ │ [View] [Save] [Share]                   │ │ │
│ │[Apply]  │ │ │ └─────────────────────────────────────────┘ │ │
│ │[Clear]  │ │ │                                             │ │
│ │         │ │ │ ┌─────────────────────────────────────────┐ │ │
│ └─────────┘ │ │ │ ⭐ 92% Machine Learning Breakthrough     │ │ │
│             │ │ │ 📅 5 hours ago • 📑 Research Paper       │ │ │
│             │ │ │ New algorithms show 40% improvement...   │ │ │
│             │ │ │ [View] [Save] [Share]                   │ │ │
│             │ │ └─────────────────────────────────────────┘ │ │
│             │ │                                             │ │
│             │ │ [Load More Results...]                      │ │
│             │ └─────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

#### 3.3.2 Search Results Detail View
```
┌─────────────────────────────────────────────────────────────────┐
│ < Back to Results                              [🔖] [📧] [🔗]    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ AI Revolution in Healthcare: A Comprehensive Analysis           │
│ ────────────────────────────────────────────────────────────   │
│                                                                 │
│ 📅 Published: March 15, 2024                                   │
│ 📰 Source: TechNews.com                                         │
│ 👤 Author: Dr. Sarah Johnson                                   │
│ ⭐ Similarity: 95%                                             │
│ 🏷️ Tags: AI, Healthcare, Technology, Innovation               │
│                                                                 │
│ ─────────────────────────────────────────────────────────────── │
│                                                                 │
│ 📄 Article Content:                                            │
│                                                                 │
│ The healthcare industry is experiencing unprecedented           │
│ transformation through artificial intelligence implementation.  │
│ Recent studies indicate that AI-powered diagnostic tools...     │
│                                                                 │
│ [Continue reading...]                                           │
│                                                                 │
│ ─────────────────────────────────────────────────────────────── │
│                                                                 │
│ 🤖 AI Summary:                                                 │
│ This article discusses the implementation of AI in healthcare   │
│ systems, highlighting diagnostic improvements, cost reduction,   │
│ and patient outcome enhancements. Key findings include...      │
│                                                                 │
│ ─────────────────────────────────────────────────────────────── │
│                                                                 │
│ 🔗 Related Documents:                                          │
│ • Machine Learning in Medical Imaging (89% similar)            │
│ • Healthcare AI Ethics and Guidelines (85% similar)            │
│ • Future of Digital Health Technologies (82% similar)          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 3.4 Content Management Interface

#### 3.4.1 Document Library
```
┌─────────────────────────────────────────────────────────────────┐
│ Content Management                    [+ Upload] [📥 Bulk Import]│
├─────────────────────────────────────────────────────────────────┤
│ ┌─────────┐ │ ┌─────────────────────────────────────────────┐ │
│ │Filters  │ │ │          Document Library                   │ │
│ │         │ │ │                                             │ │
│ │📊 View  │ │ │ 🔍 Search documents... [________________]    │ │
│ │⚪ List  │ │ │                                             │ │
│ │⚫ Grid  │ │ │ Sort by: [Most Recent ▼] View: [All ▼]     │ │
│ │⚪ Table │ │ │                                             │ │
│ │         │ │ ├─────────────────────────────────────────────┤ │
│ │📅 Date  │ │ │ ☐ Select All    1,234 documents            │ │
│ │Today    │ │ │                                             │ │
│ │This Week│ │ │ ┌──────────────────────────────────────────┐│ │
│ │This Month│ │ │ │☐ 📄 AI in Healthcare Revolution         ││ │
│ │Custom   │ │ │ │   📅 2 hours ago • 📰 RSS • 3.2k words  ││ │
│ │         │ │ │ │   🏷️ ai healthcare technology           ││ │
│ │📂 Source│ │ │ │   Recent developments in AI healthcare   ││ │
│ │☐ RSS    │ │ │ │   [👁️] [✏️] [🗑️] [🔗] [⬇️]            ││ │
│ │☐ Upload │ │ │ └──────────────────────────────────────────┘│ │
│ │☐ Manual │ │ │                                             │ │
│ │         │ │ │ ┌──────────────────────────────────────────┐│ │
│ │🏷️ Tags  │ │ │ │☐ 📑 Machine Learning Trends Report      ││ │
│ │☐ ai     │ │ │ │   📅 1 day ago • 📎 Upload • 8.5k words ││ │
│ │☐ tech   │ │ │ │   🏷️ ml trends analysis report          ││ │
│ │☐ report │ │ │ │   Comprehensive analysis of current ML   ││ │
│ │         │ │ │ │   [👁️] [✏️] [🗑️] [🔗] [⬇️]            ││ │
│ │Actions  │ │ │ └──────────────────────────────────────────┘│ │
│ │[Export] │ │ │                                             │ │
│ │[Delete] │ │ │ [📄] [📄] [📄] [📄] [📄] ... More items    │ │
│ │[Tag]    │ │ │                                             │ │
│ └─────────┘ │ │ Pages: [1] 2 3 4 5 ... 25  [Next >]       │ │
│             │ └─────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

#### 3.4.2 Document Upload Interface
```
┌─────────────────────────────────────────────────────────────────┐
│ Upload New Document                                   [✖️ Close] │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │                  📁 Drag & Drop Files Here                  │ │
│ │                          or                                 │ │
│ │                    [Browse Files...]                       │ │
│ │                                                             │ │
│ │     Supported formats: PDF, DOC, DOCX, TXT, HTML, CSV      │ │
│ │              Maximum size: 16MB per file                   │ │
│ └─────────────────────────────────────────────────────────────┘ │
│                                                                 │
│ 📄 Selected Files:                                             │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ ✅ research_paper.pdf (2.3 MB)                       [✖️]   │ │
│ │ ⏳ annual_report.docx (1.8 MB) - Processing...       [✖️]   │ │
│ │ ❌ large_file.pdf (18 MB) - Too large               [✖️]   │ │
│ └─────────────────────────────────────────────────────────────┘ │
│                                                                 │
│ Document Details:                                               │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ Title: [Auto-detected from filename            ]            │ │
│ │ Tags:  [ai, research, paper                   ] [+]        │ │
│ │ Source: [Manual Upload          ▼]                         │ │
│ │ Notes: [Optional description...                ]            │ │
│ │                                                             │ │
│ │ ☐ Auto-generate summary using AI                           │ │
│ │ ☐ Extract metadata automatically                           │ │
│ │ ☐ Send notification when processing complete               │ │
│ └─────────────────────────────────────────────────────────────┘ │
│                                                                 │
│                              [Cancel] [Upload & Process]        │
└─────────────────────────────────────────────────────────────────┘
```

### 3.5 Analytics Dashboard

#### 3.5.1 Analytics Overview
```
┌─────────────────────────────────────────────────────────────────┐
│ Analytics Dashboard               📅 Last 30 Days ▼  [🔄 Refresh]│
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────┐ │
│ │  📄 Total    │ │  🔍 Total    │ │  📈 Active   │ │ ⏱️ Avg    │ │
│ │  Documents   │ │  Searches    │ │  Sources     │ │ Response  │ │
│ │              │ │              │ │              │ │  Time     │ │
│ │    1,234     │ │     567      │ │      15      │ │  1.2s     │ │
│ │   (+12%)     │ │   (+8%)      │ │   (+2 new)   │ │ (-0.3s)   │ │
│ └──────────────┘ └──────────────┘ └──────────────┘ └──────────┘ │
│                                                                 │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │               📊 Content Growth Over Time                   │ │
│ │ 1400 │                                                     │ │
│ │ 1200 │                                    ▄▄▄              │ │
│ │ 1000 │                            ▄▄▄▄▄▄▄   ▄             │ │
│ │  800 │                    ▄▄▄▄▄▄▄▄           ▄▄           │ │
│ │  600 │            ▄▄▄▄▄▄▄                     ▄▄         │ │
│ │  400 │    ▄▄▄▄▄▄▄▄                             ▄▄        │ │
│ │  200 │▄▄▄▄                                       ▄▄      │ │
│ │    0 └─────┬─────┬─────┬─────┬─────┬─────┬─────┬─────     │ │
│ │      Jan   Feb   Mar   Apr   May   Jun   Jul   Aug       │ │
│ └─────────────────────────────────────────────────────────────┘ │
│                                                                 │
│ ┌──────────────────────────┐ ┌─────────────────────────────────┐ │
│ │     🔥 Top Keywords      │ │        📂 Content Sources       │ │
│ │                          │ │                                 │ │
│ │ 1. Artificial Intelligence│ │ RSS Feeds        45%  ████████ │ │
│ │    45 documents          │ │ Manual Upload    30%  ██████   │ │
│ │ 2. Machine Learning      │ │ Web Scraping     15%  ███      │ │
│ │    32 documents          │ │ API Import       10%  ██       │ │
│ │ 3. Startup Funding       │ │                                 │ │
│ │    28 documents          │ │ ┌─────────────────────────────┐ │ │
│ │ 4. Technology Companies  │ │ │     📈 Search Patterns     │ │ │
│ │    24 documents          │ │ │                             │ │ │
│ │ 5. Investment Trends     │ │ │ Peak Hours: 9-11 AM        │ │ │
│ │    21 documents          │ │ │ Avg Queries: 12/day        │ │ │
│ │ 6. Innovation            │ │ │ Top Query: "AI trends"      │ │ │
│ │    18 documents          │ │ └─────────────────────────────┘ │ │
│ │ 7. Research Papers       │ │                                 │ │
│ │    15 documents          │ └─────────────────────────────────┘ │
│ └──────────────────────────┘                                   │
└─────────────────────────────────────────────────────────────────┘
```

#### 3.5.2 Content Clustering Visualization
```
┌─────────────────────────────────────────────────────────────────┐
│ Content Clusters Analysis                   [📊 Export] [⚙️ Settings]│
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │                   🌐 Knowledge Map                          │ │
│ │                                                             │ │
│ │     ●────────●  AI & Machine Learning                      │ │
│ │    ╱│      ╱ ╲  (45 documents)                             │ │
│ │   ╱ │     ╱   ●                                            │ │
│ │  ●  │    ╱   ╱ ╲                                           │ │
│ │   ╲ │   ╱   ╱   ●  Technology Trends                      │ │
│ │    ╲│  ╱   ╱   ╱   (32 documents)                         │ │
│ │     ●─────╱───╱                                            │ │
│ │          ╱   ╱                                             │ │
│ │         ●───●  Business & Startups                         │ │
│ │              ╲  (28 documents)                             │ │
│ │               ╲                                            │ │
│ │                ●  Research Papers                          │ │
│ │                   (24 documents)                           │ │
│ │                                                             │ │
│ │ Legend: ● Cluster Center  ── Strong Relationship           │ │
│ └─────────────────────────────────────────────────────────────┘ │
│                                                                 │
│ Cluster Details:                                                │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ 🤖 AI & Machine Learning                                    │ │
│ │ ────────────────────────────────────────────────────────────│ │
│ │ Documents: 45  │  Growth: +15% this month                  │ │
│ │ Key Terms: artificial intelligence, neural networks, deep  │ │
│ │           learning, algorithms, automation                 │ │
│ │ Sources: TechCrunch (40%), ArXiv (30%), MIT News (20%)    │ │
│ │ [View All Documents] [Export Cluster]                     │ │
│ └─────────────────────────────────────────────────────────────┘ │
│                                                                 │
│ Cross-Cluster Insights:                                         │
│ • AI & Technology clusters show 85% content overlap            │
│ • Business cluster gaining traction with +25% growth           │
│ • Research cluster has highest engagement (avg 4.2 views/doc)  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 3.6 Settings & Configuration

#### 3.6.1 Settings Dashboard
```
┌─────────────────────────────────────────────────────────────────┐
│ Settings                                                        │
├─────────────────────────────────────────────────────────────────┤
│ ┌─────────────┐ │ ┌─────────────────────────────────────────┐   │
│ │ 👤 Account  │ │ │              Account Settings           │   │
│ │ 🔔 Notifications│ │                                         │   │
│ │ 📡 RSS Sources │ │ Username: [john_doe           ]        │   │
│ │ 🤖 AI Settings │ │ Email:    [john@example.com   ]        │   │
│ │ 🔐 Security    │ │                                         │   │
│ │ 📊 Data Export │ │ ┌─────────────────────────────────────┐ │   │
│ │ 🎨 Appearance  │ │ │ Change Password                     │ │   │
│ │ 🔧 Advanced    │ │ │ Current:  [_______________]         │ │   │
│ │               │ │ │ New:      [_______________]         │ │   │
│ │               │ │ │ Confirm:  [_______________]         │ │   │
│ │               │ │ │           [Update Password]         │ │   │
│ │               │ │ └─────────────────────────────────────┘ │   │
│ │               │ │                                         │   │
│ │               │ │ Account Activity:                       │   │
│ │               │ │ • Last login: March 15, 2024 10:30 AM  │   │
│ │               │ │ • Account created: January 10, 2024    │   │
│ │               │ │ • Total documents: 1,234               │   │
│ │               │ │ • Total searches: 567                  │   │
│ │               │ │                                         │   │
│ │               │ │ ┌─────────────────────────────────────┐ │   │
│ │               │ │ │ ⚠️  Danger Zone                     │ │   │
│ │               │ │ │                                     │ │   │
│ │               │ │ │ [Export All Data]                  │ │   │
│ │               │ │ │ [Delete Account]                   │ │   │
│ │               │ │ └─────────────────────────────────────┘ │   │
│ └─────────────┘ │ └─────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

#### 3.6.2 RSS Sources Configuration
```
┌─────────────────────────────────────────────────────────────────┐
│ RSS Sources Management                          [+ Add Source]  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ Active Sources (15):                                            │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ ✅ TechCrunch                                               │ │
│ │ 🔗 https://techcrunch.com/feed/                             │ │
│ │ 📊 245 articles • ⏰ Updated 5 min ago • 🔄 Every 30 min    │ │
│ │ 🏷️ Auto-tags: tech, startup, funding                       │ │
│ │ [⚙️ Settings] [⏸️ Pause] [🗑️ Delete]                        │ │
│ └─────────────────────────────────────────────────────────────┘ │
│                                                                 │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ ✅ Hacker News                                              │ │
│ │ 🔗 https://hnrss.org/frontpage                              │ │
│ │ 📊 189 articles • ⏰ Updated 2 min ago • 🔄 Every 15 min    │ │
│ │ 🏷️ Auto-tags: tech, programming, discussion                │ │
│ │ [⚙️ Settings] [⏸️ Pause] [🗑️ Delete]                        │ │
│ └─────────────────────────────────────────────────────────────┘ │
│                                                                 │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ ⚠️ MIT Technology Review                                    │ │
│ │ 🔗 https://www.technologyreview.com/feed/                   │ │
│ │ 📊 56 articles • ❌ Failed 2 hours ago • 🔄 Every 1 hour    │ │
│ │ 🏷️ Auto-tags: research, innovation, science               │ │
│ │ [⚙️ Settings] [🔄 Retry] [🗑️ Delete]                        │ │
│ └─────────────────────────────────────────────────────────────┘ │
│                                                                 │
│ Global Settings:                                                │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ 🔄 Default Update Frequency: [30 minutes ▼]                │ │
│ │ 🤖 Auto-generate summaries: ☑️ Enabled                     │ │
│ │ 🏷️ Auto-tag articles: ☑️ Enabled                           │ │
│ │ 📧 Email notifications: ☑️ For new sources only            │ │
│ │ 🗑️ Auto-cleanup old articles: [90 days ▼]                  │ │
│ └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. Mobile Responsive Design

### 4.1 Mobile Navigation
```
┌─────────────────────┐
│ ☰  XU-News  👤     │ Mobile Header
├─────────────────────┤
│                     │
│ ┌─────────────────┐ │
│ │ 🔍 Search here  │ │ Quick Search
│ │ [_____________] │ │
│ └─────────────────┘ │
│                     │
│ 📊 Quick Stats      │
│ ┌─────────────────┐ │
│ │ 📄 1,234 docs   │ │
│ │ 🔍 567 searches │ │
│ │ 📈 15 sources   │ │
│ └─────────────────┘ │
│                     │
│ 📱 Recent Activity  │
│ • New articles (5m) │
│ • AI search (1h)    │
│ • Upload doc (2h)   │
│                     │
│ [View All Activity] │
│                     │
└─────────────────────┘

┌─────────────────────┐
│ ☰ Menu              │ Slide-out Navigation
├─────────────────────┤
│ 🏠 Dashboard        │
│ 🔍 Search           │
│ 📄 Documents        │
│ 📊 Analytics        │
│ ⚙️ Sources          │
│ 📧 Notifications    │
│ ⚙️ Settings         │
│                     │
│ ─────────────────── │
│                     │
│ 📂 Quick Folders    │
│ > Research          │
│ > Tech News         │
│ > Reports           │
│                     │
│ ─────────────────── │
│                     │
│ 👤 John Doe         │
│ 🚪 Logout           │
└─────────────────────┘
```

### 4.2 Mobile Search Interface
```
┌─────────────────────┐
│ ← Search            │
├─────────────────────┤
│                     │
│ ┌─────────────────┐ │
│ │ What to find?   │ │
│ │ [_____________] │ │
│ │           [🔍]  │ │
│ └─────────────────┘ │
│                     │
│ 🕐 Recent Searches  │
│ • AI trends         │
│ • startup news      │
│ • tech innovation   │
│                     │
│ 🔥 Popular Tags     │
│ [ai] [tech] [news]  │
│ [research] [startup]│
│                     │
│ ⚙️ [Filters] [Voice]│
│                     │
└─────────────────────┘

┌─────────────────────┐
│ ← Results (24)      │
├─────────────────────┤
│                     │
│ ⭐ 95% AI Healthcare│
│ 📅 2h ago • TechNews│
│ Latest AI developments
│ in healthcare show... │
│ [👁️] [🔗] [⭐]       │
│ ─────────────────── │
│                     │
│ ⭐ 92% ML Breakthrough│
│ 📅 5h ago • Research│
│ New ML algorithms    │
│ show 40% improvement │
│ [👁️] [🔗] [⭐]       │
│ ─────────────────── │
│                     │
│ [Load More...]      │
│                     │
└─────────────────────┘
```

---

## 5. User Experience Flow

### 5.1 New User Onboarding Flow
```
Step 1: Registration
┌─────────────────────┐
│  Welcome to         │
│  XU-News AI-RAG     │
│                     │
│  Create your        │
│  knowledge base     │
│                     │
│  [Get Started]      │
└─────────────────────┘

Step 2: Basic Setup
┌─────────────────────┐
│  Let's set up your  │
│  first RSS sources  │
│                     │
│  ☐ Technology News  │
│  ☐ Business Updates │
│  ☐ Research Papers  │
│  ☐ Industry Reports │
│                     │
│  [Continue]         │
└─────────────────────┘

Step 3: AI Preferences
┌─────────────────────┐
│  AI Preferences     │
│                     │
│  Auto-summarize:    │
│  ⚫ Always          │
│  ⚪ Ask me          │
│  ⚪ Never           │
│                     │
│  Auto-tag articles: │
│  ☑️ Enable          │
│                     │
│  [Finish Setup]     │
└─────────────────────┘

Step 4: Dashboard Tour
┌─────────────────────┐
│  🎯 Quick Tour      │
│                     │
│  1. Search anything │
│  2. Upload documents│
│  3. View analytics  │
│  4. Manage sources  │
│                     │
│  [Start Tour]       │
│  [Skip to Dashboard]│
└─────────────────────┘
```

### 5.2 Search User Flow
```
1. Query Entry → 2. Processing → 3. Results → 4. Detail View
      ↓              ↓            ↓            ↓
┌──────────┐   ┌──────────┐  ┌──────────┐  ┌──────────┐
│ Type     │   │ AI       │  │ Ranked   │  │ Full     │
│ question │ → │ searches │ →│ results  │ →│ article  │
│          │   │ knowledge│  │ with     │  │ with AI  │
│          │   │ base     │  │ scores   │  │ summary  │
└──────────┘   └──────────┘  └──────────┘  └──────────┘
      ↓              ↓            ↓            ↓
  Natural         Vector      Similarity    Related
  language       search +     ranking +     documents
  processing     external     reranking     suggestions
                 search
```

### 5.3 Content Management Flow
```
1. Upload → 2. Processing → 3. Indexing → 4. Available
     ↓           ↓            ↓           ↓
┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐
│ File    │  │ Extract │  │ Generate│  │ Search- │
│ upload  │→ │ text &  │→ │ vectors │→ │ able in │
│ or text │  │ metadata│  │ & store │  │ system  │
└─────────┘  └─────────┘  └─────────┘  └─────────┘
     ↓           ↓            ↓           ↓
  Validation   AI analysis  FAISS index  User can
  & format     & tagging    updates      find it
  detection
```

---

## 6. Accessibility Specifications

### 6.1 WCAG 2.1 AA Compliance
- **Color Contrast**: Minimum 4.5:1 ratio for normal text, 3:1 for large text
- **Keyboard Navigation**: All interactive elements accessible via keyboard
- **Screen Reader Support**: Proper ARIA labels and semantic HTML
- **Focus Management**: Clear focus indicators and logical tab order
- **Alternative Text**: Descriptive alt text for all images and icons

### 6.2 Accessibility Features
```html
<!-- Example accessible components -->
<button aria-label="Search knowledge base" aria-describedby="search-help">
  <span class="sr-only">Search</span>
  🔍
</button>

<div role="main" aria-labelledby="results-heading">
  <h1 id="results-heading">Search Results</h1>
  <div role="region" aria-live="polite" aria-label="Search status">
    Found 24 results for "AI trends"
  </div>
</div>

<nav aria-label="Main navigation">
  <ul role="menubar">
    <li role="menuitem"><a href="/dashboard">Dashboard</a></li>
    <li role="menuitem"><a href="/search">Search</a></li>
  </ul>
</nav>
```

### 6.3 Responsive Design Breakpoints
```css
/* Mobile First */
.container {
  padding: 16px;
  max-width: 100%;
}

/* Tablet */
@media (min-width: 768px) {
  .container {
    padding: 24px;
    max-width: 1024px;
  }
  
  .sidebar {
    display: block;
    width: 240px;
  }
}

/* Desktop */
@media (min-width: 1024px) {
  .container {
    padding: 32px;
    max-width: 1280px;
  }
  
  .main-content {
    margin-left: 240px;
  }
}

/* Large Desktop */
@media (min-width: 1280px) {
  .container {
    max-width: 1440px;
  }
}
```

---

## 7. Animation & Interaction Guidelines

### 7.1 Micro-interactions
- **Loading States**: Skeleton screens and progress indicators
- **Hover Effects**: Subtle elevation and color changes
- **Transitions**: Smooth 200-300ms transitions for state changes
- **Feedback**: Visual confirmation for user actions

### 7.2 Loading States
```css
/* Loading skeleton for search results */
.skeleton-card {
  background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
  background-size: 200% 100%;
  animation: loading 1.5s infinite;
}

@keyframes loading {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

/* Success animation */
.success-checkmark {
  animation: checkmark 0.6s ease-in-out;
}

@keyframes checkmark {
  0% { transform: scale(0); }
  50% { transform: scale(1.2); }
  100% { transform: scale(1); }
}
```

---

## Conclusion

This prototype design document provides comprehensive UI/UX specifications for the XU-News-AI-RAG system, covering:

1. **Visual Design System**: Consistent colors, typography, and spacing
2. **Interface Layouts**: Detailed wireframes for all major screens
3. **User Flows**: Step-by-step interaction patterns
4. **Responsive Design**: Mobile-first approach with tablet and desktop variations
5. **Accessibility**: WCAG 2.1 AA compliance specifications
6. **Micro-interactions**: Smooth animations and loading states

The design emphasizes usability, accessibility, and modern web standards while providing an intuitive interface for managing and searching through large knowledge bases with AI assistance.

---