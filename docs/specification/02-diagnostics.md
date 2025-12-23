---
title: "Compiler Diagnostics and Error Messages"
section: 2
order: 2
---

# Compiler Diagnostics and Error Messages

================================================================================

One of Pyrite's highest-priority design goals is to make the compiler a teacher, 
not just an error reporter. Exceptional compiler diagnostics are the primary 
mechanism for delivering on Pyrite's promise of transparency and approachability.

Research and developer surveys consistently show that compiler error quality is 
among the top factors in language satisfaction. Rust's success is strongly tied 
to rustc's famous diagnostics, which teach ownership and borrowing through clear, 
actionable error messages.

2.1 Error Message Design Principles
--------------------------------------------------------------------------------

Every Pyrite compiler error follows a structured format:

1. WHAT HAPPENED: Clear statement of the error
2. WHY IT'S A PROBLEM: Explanation of the underlying issue
3. WHAT TO DO NEXT: Concrete suggestions for fixes (often multiple options)
4. LOCATION CONTEXT: Precise source highlighting with multi-line context

Example error format:

    error[P0234]: cannot use moved value 'data'
      ----> main.py:15:10
       |
    12 |     let data = List[int]([1, 2, 3])
       |         -------- value allocated here
    13 |     process(data)
       |             -------- value moved here (ownership transferred to 'process')
    14 |     # ... other code ...
    15 |     print(data.length())
       |          ^^^^ cannot use 'data' after it was moved
       |
       = note: 'data' was moved on line 13 when passed to 'process'
       = help: if you want to use 'data' again, consider:
               1. Pass a reference instead: process(&data)
               2. Clone the data: process(data.clone())
               3. Have 'process' return ownership after using it
       = explain: Run 'pyritec --explain P0234' for detailed explanation

2.2 Ownership and Borrowing Diagnostics
--------------------------------------------------------------------------------

Because ownership and borrowing are novel concepts for many programmers, Pyrite 
provides specialized diagnostics with timeline visualizations:

Borrow conflict example:

    error[P0502]: cannot borrow 'config' as mutable while also borrowed as immutable
      ----> main.py:23:5
       |
    20 |     let reader = &config           # immutable borrow starts
       |                  -------------- immutable borrow occurs here
    21 |     
    22 |     print(reader.get_value())      # immutable borrow used
    23 |     config.update("key", "value")  # mutable borrow attempted
       |     ^^^^^^ mutable borrow occurs here
    24 |     
    25 |     print(reader.get_value())      # immutable borrow used again
       |           ------------ immutable borrow later used here
       |
       = Timeline of borrows:
         Line 20: 'config' immutably borrowed → stored in 'reader'
         Line 23: Attempted to mutably borrow 'config' (CONFLICT)
         Line 25: 'reader' still needs immutable access
       
       = Ownership flow visualization:
         
         config (owner)
           │
           ├─[L20]─→ &config ─→ reader (immutable borrow active)
           │                      │
           │                      │ (borrow still alive)
           │                      │
           ├─[L23]─→ &mut config ──X ERROR: conflicts with existing borrow
           │
           └─[L25]─→ reader.get_value() (uses immutable borrow)
       
       = help: The compiler cannot allow mutable access while 'reader' exists
               because 'reader' expects 'config' to remain unchanged.
               
               Possible fixes:
               1. Complete all reads before modifying:
                  print(reader.get_value())
                  drop(reader)  # or let it go out of scope
                  config.update("key", "value")
               
               2. Restructure to avoid overlapping borrows
       
       = explain: Run 'pyritec --explain P0502' for borrowing rules
       = visual: Run 'pyritec --explain P0502 --visual' for interactive diagram

2.3 Memory and Performance Diagnostics
--------------------------------------------------------------------------------

Pyrite's cost-transparency philosophy extends to compiler warnings about 
expensive operations:

Allocation warning example:

    warning[P1050]: heap allocation in loop body
      ----> main.py:45:13
       |
    43 |     for i in 0..1000:
    44 |         var text = String.new()  # allocated on heap
    45 |         text.push_str("item ")   # potential reallocation
       |              ^^^^^^^^ string may reallocate here
    46 |         text.push_str(i.to_string())  # likely reallocation
       |              ^^^^^^^^ string may reallocate here
       |
       = performance: This loop may allocate 1000+ times
       = help: Consider allocating once before the loop:
               
               var text = String.with_capacity(50)
               for i in 0..1000:
                   text.clear()
                   text.push_str("item ")
                   text.push_str(i.to_string())
       
       = note: Use #[allow(heap_in_loop)] to suppress this warning

Copy warning example:

    warning[P1051]: large value copied implicitly
      ----> main.py:78:18
       |
    76 |     struct ImageBuffer:
    77 |         data: [u8; 1_000_000]  # 1 MB fixed-size array
    78 |     
    79 |     fn process(img: ImageBuffer):  # takes ownership by copy
       |                     ^^^^^^^^^^^ 1 MB copied on each call
       |
       = performance: ImageBuffer is 1,000,000 bytes and will be copied when 
                      passed by value
       = help: Consider taking a reference instead:
               
               fn process(img: &ImageBuffer):  # borrows, no copy
               
               Or if mutation is needed:
               
               fn process(img: &mut ImageBuffer):

2.4 Explain System
--------------------------------------------------------------------------------

Every compiler error and warning has a unique error code (e.g., P0234, P1050) 
that maps to detailed explanations accessible via:

    pyritec --explain P0234

This displays:

• Full conceptual explanation of the issue
• Multiple code examples (both incorrect and correct versions)
• Link to relevant language documentation chapter
• Common pitfalls and patterns
• Performance implications (if applicable)

The explain system serves as interactive documentation, teaching language 
concepts at the moment developers encounter problems.

Enhanced Visual Mode
~~~~~~~~~~~~~~~~~~~~~

For ownership and borrowing errors, which are the hardest concepts for 
newcomers, Pyrite offers enhanced visualizations:

    pyritec --explain P0502 --visual

This generates an interactive diagram showing:

1. **Ownership timeline:** When values are created, moved, borrowed, and dropped
2. **Borrow scope visualization:** Start and end points of each borrow
3. **Conflict points:** Exactly where and why incompatible accesses occur
4. **Data flow graph:** How ownership flows through function calls

Example visual output (ASCII art in terminal, interactive in IDE):

    Ownership Flow for 'data'
    ═════════════════════════
    
    Line 12: let data = List[int]([1,2,3])
             ┌─────┐
             │data │ ← OWNER
             └─────┘
                │
                │ (owns heap allocation)
                │
    Line 13: process(data)
                │
                └──→ MOVED to process() parameter
                     ┌─────────┐
                     │process()│
                     └─────────┘
                         │
                         │ (now owns the list)
                         │
                     [list freed here when process() returns]
    
    Line 15: print(data.length())
             ┌─────┐
             │data │ ← INVALID (moved away on line 13)
             └─────┘
                │
                X ERROR: Cannot use moved value

    Solution paths:
    ═══════════════
    
    Path 1: Clone before moving
    ────────────────────────────
    Line 13: process(data.clone())  ← data remains valid
    
    Path 2: Use a reference
    ───────────────────────
    Line 13: process(&data)  ← borrow instead of move
    
    Path 3: Get ownership back
    ──────────────────────────
    Line 13: data = process(data)  ← function returns ownership

For complex scenarios with multiple borrows:

    Borrow Conflict Analysis
    ════════════════════════
    
    Variable: config
    
    Timeline:
    ─────────
    Line 20: let reader = &config
             │
             ├──→ Immutable borrow starts (&config)
             │    Stored in 'reader'
             │
    Line 22: print(reader.get_value())
             │    Uses immutable borrow ✓
             │
    Line 23: config.update("key", "value")
             │
             X    Attempted mutable borrow (&mut config)
             │    CONFLICT: Immutable borrow still active!
             │
    Line 25: print(reader.get_value())
                  Uses immutable borrow (why it's still active)

    Conflict Resolution:
    ═══════════════════
    
    The mutable borrow on Line 23 cannot coexist with the
    immutable borrow in 'reader' because:
    
      • 'reader' expects 'config' to remain unchanged
      • Mutable access could invalidate 'reader's assumptions
      • Rust's/Pyrite's safety: no aliasing + mutation
    
    Fix: End the immutable borrow before mutating:
    
      let reader = &config
      print(reader.get_value())
      drop(reader)           ← Explicitly end borrow
      config.update(...)     ← Now safe to mutate

IDE Integration:
  • VSCode/IntelliJ plugins render interactive visualizations
  • Hover over variables to see lifetime spans
  • Click error codes to open visual explain mode
  • Animated flow for move/borrow operations

This visual enhancement transforms the hardest part of Pyrite (ownership) from 
"read text and imagine" to "see the flow directly." It's the difference between 
reading about chess moves vs. seeing the board.

2.5 IDE Hover: Ownership and Performance Metadata
--------------------------------------------------------------------------------

To make memory management and performance characteristics immediately visible, 
Pyrite's Language Server Protocol (LSP) implementation provides rich hover 
tooltips that show ownership state, memory layout, and cost implications.

Variable Hover Information
~~~~~~~~~~~~~~~~~~~~~~~~~~

Hovering over any variable shows:

    let data = List[int]([1, 2, 3])
         ^^^^
         Hover shows:
         
         Type: List[int]
         Badges: [Heap] [Move] [MayAlloc]
         
         Memory:
           • Stack: 24 bytes (ptr + len + cap)
           • Heap: 12 bytes (3 × 4-byte integers)
           • Total: 36 bytes
         
         Ownership:
           • Owner: 'data' (owned value)
           • Moved: No
           • Borrowed: Not currently borrowed
         
         Next risks:
           ⚠️  Passing to function will move (data becomes invalid)
           ✓  Use &data to borrow instead

After a move:

    process(data)
    print(data.length())  # Error
          ^^^^
          Hover shows:
          
          Type: List[int] (MOVED)
          
          Ownership:
           • Owner: None (moved on line 5 to 'process')
           • Moved: Line 5, process(data)
           • Cannot be used
          
          Fix:
           • Option 1: Pass &data to borrow
           • Option 2: Clone: process(data.clone())
           • Run 'quarry fix' for automatic correction

Function Parameter Hover
~~~~~~~~~~~~~~~~~~~~~~~~~

Hovering over function signatures shows parameter behavior:

    fn process(list: List[int]) -> int:
                     ^^^^^^^^^^
                     Hover shows:
                     
                     Parameter: list
                     Type: List[int]
                     Ownership: Takes ownership (consumes)
                     
                     ⚠️  Warning: This function takes ownership
                     Caller loses access to the value after call
                     
                     Consider: &List[int] to borrow instead

For reference parameters:

    fn sum(numbers: &[int]) -> int:
                    ^^^^^^
                    Hover shows:
                    
                    Parameter: numbers
                    Type: &[int] (borrowed slice)
                    Ownership: Borrows (read-only)
                    
                    ✓  Caller retains ownership
                    ✓  No allocation or copy
                    ✓  Zero-cost abstraction

Performance Cost Hover
~~~~~~~~~~~~~~~~~~~~~~

Hovering over operations shows their performance characteristics:

    let copy = large_buffer
               ^^^^^^^^^^^^
               Hover shows:
               
               Operation: Copy
               Cost: 4096 bytes copied
               
               Type: ImageBuffer
               Size: 4 KB
               
               ⚠️  Large copy warning
               Consider: Use reference (&large_buffer)
               Estimated impact: 4 KB memcpy (~500 cycles)

For allocations:

    let list = List[int].new()
               ^^^^^^^^^^^^^^^
               Hover shows:
               
               Operation: Heap allocation
               Cost: Initial capacity: 0 bytes
                     Growth: Will reallocate on first push
               
               💡 Tip: Use with_capacity(n) to avoid reallocation
               Example: List[int].with_capacity(10)

Borrow Conflict Context
~~~~~~~~~~~~~~~~~~~~~~~

When hovering in a borrow conflict scenario:

    let reader = &config
    config.update("key", "val")  # Error
    ^^^^^^
    Hover shows:
    
    Variable: config
    Type: Config
    
    Borrow Status:
      ⚠️  Immutably borrowed by 'reader' (line 20)
      ⚠️  Cannot mutate while borrowed
    
    Active borrows:
      • Line 20: &config → reader (immutable)
      • Used on line 25: reader.get_value()
    
    To fix:
      • End 'reader' borrow before mutating
      • Use drop(reader) or let it go out of scope

Type Information Hover
~~~~~~~~~~~~~~~~~~~~~~

Hovering over type names shows memory characteristics:

    struct Point:
           ^^^^^
           Hover shows:
           
           Type: Point
           Badges: [Stack] [Copy] [ThreadSafe]
           
           Memory Layout:
             • Size: 8 bytes (2 × i32)
             • Alignment: 4 bytes
             • Location: Stack (inline in structs)
           
           Behavior:
             • Copy: Cheap bitwise copy
             • Drop: No-op (no destructor)
             • Thread-safe: Yes (no shared state)
           
           Fields:
             • x: i32 (offset 0, 4 bytes)
             • y: i32 (offset 4, 4 bytes)
           
           Run 'quarry explain-type Point' for details

Integration with Cost Analysis
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

IDE hover information integrates with static cost analysis:

    for i in 0..1000:
        let v = List[int].new()  # In loop
                ^^^^^^^^^^^^^^^
                Hover shows:
                
                ⚠️  Allocation in loop
                
                Static analysis:
                  • Called 1000 times
                  • 1000 heap allocations
                  • Estimated cost: ~24 KB
                
                Suggestion:
                  Move allocation before loop:
                  
                  let v = List[int].with_capacity(10)
                  for i in 0..1000:
                      v.clear()
                      # use v...

Configuration
~~~~~~~~~~~~~

IDE hover detail levels are configurable:

    # .vscode/settings.json or IDE config
    {
      "pyrite.hover.level": "intermediate",  # beginner/intermediate/advanced
      "pyrite.hover.showMemoryLayout": true,
      "pyrite.hover.showPerformanceCosts": true,
      "pyrite.hover.showOwnershipFlow": true
    }

Levels:
  • Beginner: Simple ownership state, basic warnings
  • Intermediate: Memory layout, costs, suggestions (default)
  • Advanced: Full call chains, assembly hints, cache implications

Why This Matters
~~~~~~~~~~~~~~~~~

IDE hover transforms abstract concepts into visible reality:

  • **Ownership becomes tangible:** See when values move, when borrows conflict
  • **Performance becomes predictable:** See costs before profiling
  • **Learning becomes interactive:** Immediate feedback while coding
  • **Debugging becomes faster:** Understand state without println debugging

Research suggests that visual feedback can accelerate learning of ownership concepts 
compared to text-only error messages (specific studies show improvements in the 40-60% 
range, though results vary by study methodology). Making ownership visible in real-time 
while coding (not just at compile time) addresses a significant gap in teaching systems 
programming.

Implementation: Beta Release, integrated with pyrite-lsp server. Requires coordination 
with static analyzer and quarry cost system to provide accurate information.

2.6 Diagnostic Quality Standards
--------------------------------------------------------------------------------

All compiler messages must meet these standards:

• Actionable: Suggest concrete fixes, not just describe the problem
• Contextual: Show enough source code to understand the issue
• Beginner-friendly: Avoid jargon or explain it inline
• Multi-solution: Present multiple approaches when applicable
• Consistent: Use uniform formatting and terminology
• Precise: Highlight exact problematic code spans

The compiler team maintains diagnostic quality as a first-class requirement, with 
dedicated review gates for error message clarity before feature acceptance.

2.7 Internationalized Error Messages (Stable Release)
--------------------------------------------------------------------------------

To achieve truly global adoption, Pyrite provides compiler
diagnostics in multiple languages, making systems programming accessible to 
non-native English speakers worldwide.

Command Usage
~~~~~~~~~~~~~

    pyritec --language=zh            # Chinese error messages
    pyritec --language=es            # Spanish error messages  
    pyritec --language=ja            # Japanese error messages
    pyritec --language=ko            # Korean error messages
    pyritec --language=pt            # Portuguese error messages
    pyritec --language=de            # German error messages
    pyritec --language=fr            # French error messages

Configuration:

    # .pyrite/config.toml or environment variable
    [compiler]
    language = "es"                  # Default to Spanish
    
    # Or environment variable
    export PYRITE_LANG=zh

Example Error Message (English):

    error[P0234]: cannot use moved value 'data'
      ----> main.py:15:10
       |
    12 |     let data = List[int]([1, 2, 3])
       |         -------- value allocated here
    13 |     process(data)
       |             -------- value moved here
    15 |     print(data.length())
       |          ^^^^ cannot use 'data' after it was moved
       |
       = help: Consider:
               1. Pass a reference: process(&data)
               2. Clone the data: process(data.clone())

Example Error Message (Chinese):

    错误[P0234]: 无法使用已移动的值 'data'
      ----> main.py:15:10
       |
    12 |     let data = List[int]([1, 2, 3])
       |         -------- 值在此分配
    13 |     process(data)
       |             -------- 值在此移动
    15 |     print(data.length())
       |          ^^^^ 值移动后无法使用 'data'
       |
       = 帮助: 考虑以下选项:
               1. 传递引用: process(&data)
               2. 克隆数据: process(data.clone())

Example Error Message (Spanish):

    error[P0234]: no se puede usar el valor movido 'data'
      ----> main.py:15:10
       |
    12 |     let data = List[int]([1, 2, 3])
       |         -------- valor asignado aquí
    13 |     process(data)
       |             -------- valor movido aquí
    15 |     print(data.length())
       |          ^^^^ no se puede usar 'data' después de moverlo
       |
       = ayuda: Considera:
               1. Pasar una referencia: process(&data)
               2. Clonar los datos: process(data.clone())

Translation Quality Standards
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Pyrite enforces high translation quality through:

1. **Native speaker translators:** Professional translations, not machine translation
2. **Technical accuracy:** Preserve precise technical meanings
3. **Consistency:** Shared terminology across all error messages
4. **Community review:** Open process for translation improvements
5. **Maintainability:** Translation infrastructure integrated with compiler

Supported Languages (Priority Order)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Stable Release (Initial Internationalization):
  • English (en) - Default
  • Chinese (zh) - 1.4B speakers, huge developer population
  • Spanish (es) - 500M speakers, Latin America growing
  • Hindi (hi) - 600M speakers, India's massive dev community

Stable Release Expansion:
  • Japanese (ja) - Major tech economy
  • Portuguese (pt) - Brazil's growing tech sector
  • Korean (ko) - Strong programming culture
  • German (de) - European tech hub
  • French (fr) - Francophone Africa + Europe
  • Russian (ru) - Eastern Europe tech community

Translation Infrastructure
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Messages stored in structured format:

    # errors/en/P0234.toml
    code = "P0234"
    title = "cannot use moved value '{name}'"
    
    [message]
    primary = "cannot use '{name}' after it was moved"
    note = "value moved here"
    help = [
        "Pass a reference: {suggestion_ref}",
        "Clone the data: {suggestion_clone}"
    ]

Community contribution workflow:

    quarry translate --language=es       # Check translation coverage
    quarry translate --validate          # Verify translation quality
    quarry translate --submit            # Submit translation PR

IDE Integration
~~~~~~~~~~~~~~~

Language selection respects IDE/OS settings:

    # VSCode/IntelliJ automatically use system language
    # Override in IDE settings:
    "pyrite.diagnostics.language": "auto"  # Match system locale
    "pyrite.diagnostics.language": "en"    # Force English
    "pyrite.diagnostics.language": "zh"    # Force Chinese

Why This Matters
~~~~~~~~~~~~~~~~~

Internationalized error messages address a critical adoption barrier:

**Global reach:**
  • 60% of programmers are non-native English speakers
  • Educational institutions in non-English countries
  • Open source contributors worldwide
  • Government contracts requiring local language support

**Accessibility:**
  • Language barriers prevent understanding complex concepts (ownership)
  • Error messages are WHERE learning happens
  • Native language reduces cognitive load for hard concepts
  • Enables instructors to teach in students' first language

**Differentiation:**
  • Almost NO compilers do this well (GCC/Clang have minimal translations)
  • Rust has basic translation but inconsistent
  • Go, Zig, Mojo: English only
  • Pyrite: First-class multilingual support from day one

**Evidence:**
  • Microsoft DevTools survey: 78% prefer native language errors
  • Educational research suggests faster concept mastery in first language (specific 
    studies show approximately 2x improvement, though results vary)
  • Adoption data: Python's success partly due to global accessibility

**Achieving widespread developer adoption requires global reach, not just 
English-speaking countries.**

Translation coverage tracking:

    $ quarry translate --language=zh --coverage
    
    Chinese Translation Coverage
    =============================
    
    Error codes: 234 / 250 (93.6%)
    Warning codes: 89 / 92 (96.7%)
    Compiler hints: 156 / 160 (97.5%)
    
    Missing translations:
      • P0891 - Advanced lifetime error
      • P0923 - Generic associated type issue
      • W1234 - Performance hint for GPU kernel
    
    Contribute: https://github.com/WulfHouse/Quarry

This infrastructure positions Pyrite to be among the first systems programming languages 
with comprehensive global 
language, accessible to the world's 26 million developers regardless of native 
language.

Implementation: Stable Release (core languages and expansion)
Priority: High (required for global adoption)

---

**Part of**: [Pyrite Language Specification](../SSOT.md)

**Previous**: [Design Goals and Philosophy](01-design-philosophy.md)

**Next**: [Syntax Overview](03-syntax.md)
