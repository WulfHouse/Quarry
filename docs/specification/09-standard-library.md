---
title: "Standard Library and Ecosystem"
section: 9
order: 9
---

# Standard Library and Ecosystem

To be a true "do-anything" language, Pyrite is bundled with a comprehensive 
standard library that makes it productive out of the box. The standard library 
is designed with the same philosophy as the language: performance, safety, and 
simplicity by default, with no hidden costs.

## 9.1 Standard Library Design Philosophy

Pyrite's standard library is "batteries included" - shipping with everything 
needed to build real applications without pulling in dozens of dependencies. The 
stdlib enables developers to evaluate Pyrite by building complete projects (web 
servers, CLI tools, games) using only built-in functionality.

The philosophy: provide excellent baseline implementations for common tasks, with 
zero magic and predictable performance.

Pit of Success: API Design Principles
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The standard library is designed to make the performant choice the obvious choice:

0. **APIs take views by default; ownership-taking is always spelled:**
   
   This is the **dominant rule** that prevents the "why did this move?" confusion:
   
   Standard (90% of APIs):
       fn parse(content: &str) -> Result[Data, Error]
       fn process(items: &[Item]) -> Summary
       fn validate(config: &Config) -> bool
   
   Ownership-taking (rare, always explicit):
       fn consume(data: List[int]) -> ProcessedData
       fn take_ownership(resource: File) -> Handle
       # These require @consumes annotation in docs
   
   Rule enforcement:
     • stdlib APIs default to borrowed views (&T, &str, &[T])
     • Taking ownership requires doc comment explaining why
     • quarry lint warns: "function takes ownership without @consumes"
     • Compiler suggests: "Consider &T instead of T"
   
   Why this matters:
     • Beginners learn "pass by reference" as default
     • Ownership transfer becomes explicit and rare
     • "Cannot use moved value" errors become uncommon
     • Code reads like high-level Python but compiles to zero-cost
   
   Exception cases (ownership-taking justified):
     • Builder pattern: consume builder to produce final type
     • Thread spawn: move data to thread (Send requirement)
     • Containers: insert/push take ownership to store
   
   This single convention prevents the #1 beginner frustration with ownership.

0.5. **Safe accessors by default; unchecked when provable:**
   
   Collection APIs provide safe accessors that bounds-check by default, with 
   optimizer elision when safety is provable at compile time:
   
   Safe accessor (Core mode default):
       let value = arr.get(i)  # Returns Optional[T], never panics
       match value:
           Some(v): process(v)
           None: handle_out_of_bounds()
   
   Direct indexing (optimizes to unchecked when safe):
       let value = arr[i]      # Bounds-checked at runtime
                               # Optimizer removes check if i provably valid
   
   Explicit unchecked (unsafe only):
       unsafe:
           let value = arr.get_unchecked(i)  # Caller guarantees validity
   
   Optimizer elision examples:
   
       # Compiler proves i is always valid, elides bounds check:
       for i in 0..arr.len():
           let value = arr[i]  # No runtime check (loop bounds prove safety)
       
       # Compiler cannot prove safety, keeps check:
       let i = user_input.parse()
       let value = arr[i]      # Runtime bounds check (prevents crash)
   
   Teaching progression:
     1. **Week 1 (Core mode):** Use .get() exclusively, learn Optional handling
     2. **Week 2:** Learn that arr[i] is checked too, but returns Result/panics
     3. **Week 3:** Understand optimizer removes checks when provable
     4. **Week 4+:** Use arr[i] knowing it's safe with compiler help
   
   API design rules:
     • Collection.get(index) → Optional[T] (safe, explicit None case)
     • Collection[index] → T (checked, panics on out-of-bounds in debug)
     • Collection.get_unchecked(index) → T (unsafe, no checks)
   
   Why this matters:
     • Beginners learn safe patterns (Optional handling)
     • Intermediate developers use direct indexing with safety
     • Optimizer makes safe code as fast as unsafe code (when provable)
     • Explicit unsafe only needed when truly required
   
   Compiler optimization examples:
   
       # Pattern 1: Iterator indices (always safe)
       for (i, item) in arr.iter().enumerate():
           let neighbor = arr[i + 1]  # Bounds check KEPT (may overflow)
       
       # Pattern 2: Proven bounds
       if i < arr.len():
           let value = arr[i]         # Bounds check ELIDED (proven safe)
       
       # Pattern 3: Fixed-size arrays
       let buffer: [u8; 256] = ...
       for i in 0..256:
           buffer[i] = 0              # Bounds check ELIDED (compile-time size)
   
   quarry cost shows which checks remain:
   
       Performance Analysis
       ====================
       
       Bounds checks (3 sites, 2 elided):
         ✓ Line 45: arr[i] - ELIDED (loop bounds prove safety)
         ✓ Line 67: buffer[idx] - ELIDED (compile-time size check)
         ⚠ Line 89: data[user_idx] - CHECKED (unprovable, keeps safety)
   
   This approach gives beginners safety by default while teaching that "fast" and 
   "safe" aren't opposed - the compiler makes safe code fast when it can prove 
   correctness.

1. **Fast path is the easy path:**
   
   Good:
       let builder = StringBuilder.with_capacity(estimated_size)
       builder.append("Hello")
       builder.append(" world")
       let result = builder.to_string()  # Single allocation
   
   Discouraged:
       let result = "Hello" + " world"   # Multiple allocations
       # String + operator marked @deprecated in stdlib
       # Compiler suggests: "Use StringBuilder for efficiency"

2. **Expensive operations look expensive:**
   
   Cheap:
       list.len()           # O(1), field access
       map.get(key)         # O(1) expected
   
   Expensive:
       list.clone()         # Explicit allocation + copy
       data.to_owned()      # Heap allocation (vs borrowing)
       vec.sort()           # O(n log n), obvious operation

3. **Default to borrowed views:**
   
   stdlib APIs prefer:
       fn parse(content: &str) -> Result[Data, Error]
       fn process(items: &[Item]) -> Summary
   
   Over:
       fn parse(content: String) -> Result[Data, Error]  # Takes ownership
       fn process(items: Vec[Item]) -> Summary           # Unnecessary move

4. **Pre-allocation is obvious:**
   
   Collections provide capacity hints:
       List::with_capacity(n)
       Map::with_capacity(n)
       String::with_capacity(n)
   
   Compiler warns when growing in loops:
       warning: list may reallocate in loop
         suggestion: pre-allocate with with_capacity()

5. **Builders for complex construction:**
   
   Instead of:
       let url = "https://" + host + ":" + port + "/" + path
   
   Provide:
       let url = UrlBuilder::new()
           .scheme("https")
           .host(host)
           .port(port)
           .path(path)
           .build()

6. **Iterators avoid allocations:**
   
   Lazy evaluation by default:
       numbers.iter()
           .filter(|x| x % 2 == 0)
           .map(|x| x * 2)
           .sum()
       # Zero intermediate collections

7. **Escape hatches clearly labeled:**
   
   When you need the expensive operation:
       data.clone()              # Explicit: makes a copy
       text.to_owned()           # Explicit: heap allocation
       list.into_vec()           # Explicit: transfer to owned
   
   Never hidden behind operator overloading or implicit conversions.

Implementation Examples
~~~~~~~~~~~~~~~~~~~~~~~

String Building:

    # BAD (stdlib actively discourages this)
    var result = ""
    for name in names:
        result = result + name + ", "  # N allocations!
    
    # GOOD (stdlib makes this easy)
    let mut builder = StringBuilder::with_capacity(names.len() * 10)
    for name in names:
        builder.append(name)
        builder.append(", ")
    let result = builder.to_string()  # 1 allocation

The stdlib might not even provide String::operator+ to prevent the antipattern.

Collection Growth:

    # Suboptimal (but works)
    let mut list = List::new()
    for i in 0..1000:
        list.push(i)  # May reallocate ~10 times
    
    # Optimal (stdlib makes this obvious)
    let mut list = List::with_capacity(1000)
    for i in 0..1000:
        list.push(i)  # Never reallocates
    
    # Compiler helps:
    warning[P1050]: list may reallocate in loop
      → suggestion: List::with_capacity(1000)

View-First APIs:

    # stdlib function signatures prefer views
    fn join(separator: &str, items: &[&str]) -> String
    fn contains(haystack: &[u8], needle: &[u8]) -> bool
    fn parse_json(text: &str) -> Result[Value, ParseError>
    
    # Callers can pass owned or borrowed data
    let result = join(", ", &vec_of_strings)      # vec deref to slice
    let result = join(", ", &["a", "b", "c"])     # array to slice
    let result = join(", ", items_as_slice)       # already a slice

Teaching Through APIs
~~~~~~~~~~~~~~~~~~~~~

The stdlib teaches performance intuition through its design:

  • If it's cheap, it's easy (len(), get())
  • If it's expensive, it's explicit (clone(), to_owned())
  • If it allocates, it's obvious (new(), with_capacity())
  • If it might reallocate, compiler warns

This is superior to documentation that says "be careful with +". The API design 
makes mistakes hard and good practices easy.

Key aspects of the standard library design:

## 9.2 Core Collections

List[T] - Dynamic Array
~~~~~~~~~~~~~~~~~~~~~~~

Heap-allocated, growable array (analogous to std::vector or Vec):

    let mut numbers = List[int].new()
    numbers.push(1)
    numbers.push(2)
    numbers.push(3)
    
    # Pre-allocate for performance
    let mut buffer = List[u8].with_capacity(1024)
    
    # Iteration
    for n in numbers:
        print(n)
    
    # Slicing
    let slice = numbers[1..3]  # elements 1-2

API guarantees:
  • Amortized O(1) push (may reallocate)
  • O(1) indexed access with bounds checking
  • O(n) insert/remove in middle
  • Capacity and length separated (explicit reallocation control)

Map[K, V] - Hash Table
~~~~~~~~~~~~~~~~~~~~~~

Key-value store with O(1) average lookup:

    let mut scores = Map[String, int].new()
    scores.insert("Alice", 100)
    scores.insert("Bob", 85)
    
    match scores.get("Alice"):
        Some(score):
            print("Alice scored:", score)
        None:
            print("Not found")
    
    # Iteration
    for (name, score) in scores:
        print(name, "-->", score)

Set[T] - Hash Set
~~~~~~~~~~~~~~~~~

Unique elements with O(1) membership testing:

    let mut seen = Set[String].new()
    seen.insert("foo")
    
    if seen.contains("foo"):
        print("Already processed")

Other Collections
~~~~~~~~~~~~~~~~~

  • LinkedList[T] - Doubly-linked list
  • BinaryHeap[T] - Priority queue
  • VecDeque[T] - Double-ended queue
  • BTreeMap[K, V] - Sorted map
  • BTreeSet[T] - Sorted set

Inline Storage Collections (Optimization Helpers)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For performance-critical code that frequently uses small collections, Pyrite 
provides inline-storage variants that avoid heap allocation when sizes are small:

SmallVec[T, N] - Inline Vector
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Stack-allocated up to N elements, spills to heap if exceeded:

    import std::collections
    
    # Common case: lists with 0-8 items
    let mut tags = SmallVec[String, 8]::new()
    
    tags.push("rust")      # On stack
    tags.push("systems")   # On stack
    tags.push("safe")      # On stack
    # ... up to 8 items stay on stack
    
    # If you exceed capacity, automatically spills to heap
    for tag in many_tags:  # If > 8 items
        tags.push(tag)     # Transparent heap allocation

Memory layout:
  • Stack size: sizeof(T) * N + pointer + length + capacity
  • Example: SmallVec[int, 8] = 64 bytes (8 ints) + 24 bytes (metadata) = 88 bytes
  • If spilled: 24 bytes stack + heap allocation

When to use:
  • Profiling shows: "Most lists have < 10 items, but a few are large"
  • Function-local collections with typical small size
  • Avoiding allocation in hot paths for common cases

Example from quarry tune:

    warning: List[Token] has median size 6, max size 247
      → Suggestion: Use SmallVec[Token, 8] for 90% zero-alloc case
      → Remaining 10% still work correctly (heap allocation)

Performance characteristics:
  • N or fewer items: Zero heap allocations, stack-only
  • More than N items: One heap allocation (same as List)
  • Still has amortized O(1) push
  • Trade-off: Larger stack footprint

SmallString[N] - Inline String
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Small String Optimization (SSO) for short strings:

    import std::collections
    
    # Most strings are short (file names, identifiers, etc.)
    let mut name = SmallString[32]::new()
    
    name.append("config")      # On stack
    name.append(".toml")       # On stack
    # Total: 11 bytes, fits in 32-byte inline buffer

Memory layout:
  • Stack size: N bytes + length byte + flags
  • Example: SmallString[32] = 32 bytes + 2 bytes = 34 bytes total
  • If exceeded: Falls back to heap-allocated String

Typical sizes:
  • SmallString[16] - Short identifiers, tags
  • SmallString[32] - File names, config keys (common default)
  • SmallString[64] - Short paths, URLs
  • SmallString[256] - Full paths, longer text

When to use:
  • Profiling shows: "90% of strings are < 30 characters"
  • Temporary string building in hot paths
  • String keys in tight loops

Example:

    fn format_log_line(level: &str, message: &str) -> SmallString[128]:
        let mut line = SmallString[128]::new()
        line.append("[")
        line.append(level)
        line.append("] ")
        line.append(message)
        return line
    
    # For typical logs: zero allocations
    # For long messages: falls back to heap gracefully

Performance win:
  • Avoids millions of small allocations for short strings
  • Cache-friendly (data inline with metadata)
  • Still correct for any length (automatic spillover)

InlineMap[K, V, N] - Small Hash Map
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Inline hash map for small key-value sets:

    import std::collections
    
    # Configuration often has 2-5 entries
    let mut flags = InlineMap[String, bool, 4]::new()
    
    flags.insert("debug", true)
    flags.insert("verbose", false)
    # ... up to 4 entries stay on stack

Memory layout:
  • Stack array of N entries (key, value, hash)
  • Linear search for small N (faster than hashing for N < 8)
  • If exceeded N entries: Converts to heap-allocated Map

When to use:
  • Small lookup tables (2-8 entries)
  • Function-local caches
  • Configuration dictionaries

Performance characteristics:
  • N or fewer entries: Zero allocations, O(N) lookup (fast for small N)
  • More than N entries: Converts to O(1) hash map on heap
  • Trade-off: Linear search (but cache-friendly, predictable)

Typical usage:

    fn parse_color(name: &str) -> Optional[Color]:
        # Static color map, 8 common colors
        const COLORS = InlineMap[&str, Color, 8]::from([
            ("red", Color.RED),
            ("green", Color.GREEN),
            ("blue", Color.BLUE),
            // ... 5 more
        ])
        
        return COLORS.get(name)  # Zero allocations, fast lookup

Integration with quarry tune
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The quarry tune command suggests inline-storage types automatically:

    $ quarry tune
    
    Performance Tuning Suggestions
    ===============================
    
    3. Use SmallVec for small arrays
       Location: src/ast.py:89
       
       Current code:
         fn parse_attributes() -> List[Attribute]:
             let mut attrs = List[Attribute].new()
             // typically returns 0-3 attributes
       
       Profile data:
         • Called 10,000 times
         • Size distribution: min=0, median=2, p95=5, max=47
         • Current cost: 10,000 heap allocations
       
       Suggested fix:
         fn parse_attributes() -> SmallVec[Attribute, 6]:
             let mut attrs = SmallVec[Attribute, 6]::new()
       
       Expected improvement:
         • Eliminates 9,500 allocations (95% case)
         • Remaining 500 calls still allocate (max > 6)
         • Estimated speedup: 12-15%
       
       [Apply] [Skip] [Explain]

This makes performance optimization mechanical: profiler identifies patterns, 
suggests specific containers, estimates improvement.

Teaching Path
~~~~~~~~~~~~~

Inline-storage types are introduced as optimization, not fundamentals:

1. **Week 1-2:** Use standard List, String, Map
   - Learn ownership and borrowing with familiar containers
   - Build working programs

2. **Week 3-4:** Profile code with quarry cost and quarry alloc
   - Identify allocation hot spots
   - See "1000 allocations in loop"

3. **Week 5+:** Optimize with inline-storage types
   - quarry tune suggests SmallVec[T, 8]
   - Apply suggestion, measure improvement
   - Understand trade-offs (stack space vs allocations)

4. **Expert:** Choose optimal sizes based on profiling
   - "Median=3, p95=7 → use N=8"
   - Balance stack footprint vs allocation avoidance

These containers are "pit of success" for performance: common patterns get easy, 
fast solutions without requiring deep expertise.

Why This Matters
~~~~~~~~~~~~~~~~~

Inline-storage containers are proven winners in production systems:

  • Rust: smallvec crate (8M downloads/month)
  • C++: llvm::SmallVector (ubiquitous in LLVM/Clang)
  • Real world: Most collections are small (< 10 items)

By including these in stdlib, Pyrite makes the fast path easy:
  • Beginners learn standard containers first
  • Intermediate developers optimize hot paths
  • quarry tune makes suggestions mechanical
  • Performance win without complexity explosion

This is the "pit of success" in action: the ergonomic choice becomes the 
performant choice for the 90% case.

## 9.3 String Handling

String Type
~~~~~~~~~~~

Immutable UTF-8 string:

    let greeting = "Hello, world!"
    let length = greeting.len()          # Byte length
    let char_count = greeting.chars().count()  # Character count
    
    # Slicing (byte indices)
    let hello = greeting[0..5]
    
    # Searching
    if greeting.contains("world"):
        print("Found it")
    
    # Splitting
    for word in greeting.split(", "):
        print(word)

StringBuilder
~~~~~~~~~~~~~

Efficient mutable string building:

    let mut builder = StringBuilder.new()
    builder.append("Hello")
    builder.append(", ")
    builder.append("world")
    let result = builder.to_string()  # Single allocation

String Formatting
~~~~~~~~~~~~~~~~~

Type-safe formatting without allocations in hot paths:

    let name = "Alice"
    let age = 30
    let msg = format("Hello, {}! You are {} years old.", name, age)
    
    # Or for performance-critical code:
    let mut buf = [u8; 256]
    let written = format_to_slice(&mut buf, "x = {}", x)

## 9.4 File and I/O Operations

File Operations
~~~~~~~~~~~~~~~

Safe file handling with Result types:

    # Reading entire file
    match File.read_to_string("config.txt"):
        Ok(contents):
            print(contents)
        Err(e):
            print("Error reading file:", e)
    
    # Writing file
    match File.write("output.txt", data):
        Ok(_):
            print("Written successfully")
        Err(e):
            print("Write error:", e)
    
    # Buffered reading
    match File.open("large.dat"):
        Ok(file):
            let reader = BufferedReader.new(file)
            for line in reader.lines():
                process(line)
        Err(e):
            print("Cannot open:", e)

Path Manipulation
~~~~~~~~~~~~~~~~~

Cross-platform path handling:

    let path = Path.new("/usr/local/bin")
    let joined = path.join("myapp")
    
    if path.exists():
        print("Directory exists")
    
    if path.is_dir():
        for entry in path.read_dir():
            print(entry.name())

## 9.5 Serialization (JSON, TOML)

JSON Support
~~~~~~~~~~~~

Built-in JSON parsing and generation:

    # Parsing
    let json_str = '{"name": "Alice", "age": 30}'
    match json.parse(json_str):
        Ok(value):
            let name = value["name"].as_string()
            let age = value["age"].as_int()
        Err(e):
            print("Parse error:", e)
    
    # Generating
    let data = json.object()
    data.set("name", "Bob")
    data.set("age", 25)
    let output = data.to_string()

TOML Support
~~~~~~~~~~~~

Configuration file format:

    match toml.parse_file("config.toml"):
        Ok(config):
            let database = config["database"]["host"].as_string()
        Err(e):
            print("Config error:", e)

Derive Serialization
~~~~~~~~~~~~~~~~~~~~

Automatic serialization for structs:

    @derive(Serialize, Deserialize)
    struct Config:
        host: String
        port: int
        debug: bool
    
    let config = Config { host: "localhost", port: 8080, debug: true }
    let json = json.to_string(config)

## 9.6 Networking

TCP Client/Server
~~~~~~~~~~~~~~~~~

    # TCP Server
    let listener = TcpListener.bind("127.0.0.1:8080")?
    for stream in listener.incoming():
        match stream:
            Ok(conn):
                handle_client(conn)
            Err(e):
                print("Connection error:", e)
    
    # TCP Client
    let mut stream = TcpStream.connect("example.com:80")?
    stream.write(b"GET / HTTP/1.0\r\n\r\n")?
    let response = stream.read_to_end()?

HTTP Client
~~~~~~~~~~~

Built-in HTTP client for common use cases:

    # Simple GET request
    let response = http.get("https://api.example.com/data")?
    print("Status:", response.status)
    print("Body:", response.text())
    
    # POST with JSON
    let data = json.object()
    data.set("name", "Alice")
    
    let response = http.post("https://api.example.com/users")
        .json(data)
        .send()?

HTTP Server (Basic)
~~~~~~~~~~~~~~~~~~~

Lightweight HTTP server for simple applications:

    fn handle_request(req: &Request) -> Response:
        if req.path == "/":
            return Response.ok("Hello, world!")
        return Response.not_found()
    
    let server = HttpServer.new("127.0.0.1:3000", handle_request)
    server.run()?

## 9.7 Time and Dates

Duration and Instant
~~~~~~~~~~~~~~~~~~~~

    let start = Instant.now()
    # ... do work ...
    let elapsed = start.elapsed()
    print("Took {} ms", elapsed.as_millis())
    
    # Sleep
    sleep(Duration.from_secs(2))

DateTime
~~~~~~~~

    let now = DateTime.now()
    print(now.format("%Y-%m-%d %H:%M:%S"))
    
    let christmas = DateTime.parse("2025-12-25", "%Y-%m-%d")?
    let days_until = christmas.duration_since(now).as_days()

## 9.8 Command-Line Argument Parsing

Args Parser
~~~~~~~~~~~

Built-in CLI argument parsing:

    let args = Args.parse()
    
    if args.has_flag("--verbose"):
        enable_verbose()
    
    let output = args.get_value("--output").unwrap_or("stdout")
    let inputs = args.get_positionals()

Or with structured parsing:

    @derive(Args)
    struct CliArgs:
        @arg(short='v', long="verbose")
        verbose: bool
        
        @arg(short='o', long="output", default="stdout")
        output: String
        
        @arg(positional)
        files: List[String]
    
    let args = CliArgs.parse()?
    if args.verbose:
        print("Verbose mode enabled")

## 9.9 Regular Expressions

Regex Support
~~~~~~~~~~~~~

    let re = Regex.new(r"\d{3}--\d{4}")?  # Phone pattern
    
    if re.is_match("555-1234"):
        print("Valid phone number")
    
    # Capture groups
    match re.captures("Call 555-1234 now"):
        Some(caps):
            print("Phone:", caps[0])
        None:
            print("No match")

## 9.10 Mathematics

Common Math Functions
~~~~~~~~~~~~~~~~~~~~~

    import math
    
    let angle = math.pi / 4.0
    let sine = math.sin(angle)
    let cosine = math.cos(angle)
    let power = math.pow(2.0, 10.0)
    let root = math.sqrt(16.0)

Random Numbers
~~~~~~~~~~~~~~

    import random
    
    let r = random.thread_rng()
    let dice = r.gen_range(1..=6)
    let coin = r.gen_bool(0.5)

## 9.11 Numerical Computing: Tensor Type (Stable Release)

For numerical computing, scientific computing, and machine learning applications, 
Pyrite provides a first-class Tensor type that combines compile-time shape 
checking with explicit memory layout control.

Design Philosophy
~~~~~~~~~~~~~~~~~

Pyrite's Tensor is NOT a full ML framework (not Numpy/PyTorch). It's a 
memory layout and indexing abstraction that composes with existing performance 
primitives (SIMD, tiling, parallelization).

Core Tensor Type
~~~~~~~~~~~~~~~~

    import std::numerics
    
    # Compile-time shape and layout
    struct Tensor[T, Shape: (int...), Layout: TensorLayout]:
        data: [T; Shape.total_size()]  # Fixed-size, stack or inline
        
        fn shape() -> (int...):
            return Shape
        
        fn get(&self, indices: (int...)) -> &T:
            # Layout-aware indexing
        
        fn get_mut(&mut self, indices: (int...)) -> &mut T:
            # Mutable access

Tensor layouts:

    enum TensorLayout:
        RowMajor     # C-style: rightmost index varies fastest
        ColMajor     # Fortran-style: leftmost index varies fastest
        Strided      # Arbitrary strides (for views)

Example usage:

    # 2D matrix (1024×768)
    let mut image = Tensor[f32, (1024, 768), RowMajor]::zeros()
    
    # Compile-time shape checking
    image.get((100, 200))  # OK
    # image.get((100, 200, 50))  # ERROR: wrong rank
    
    # Layout-aware iteration
    for i in 0..1024:
        for j in 0..768:
            image[(i, j)] = compute(i, j)

Tensor Views (Slicing)
~~~~~~~~~~~~~~~~~~~~~~

Zero-cost slicing with explicit aliasing through borrowing:

    fn process_row(row: &TensorView[f32, (768,)]):
        # Operate on borrowed view, no copy
    
    let image = Tensor[f32, (1024, 768), RowMajor]::zeros()
    process_row(image.row(10))  # Borrow row 10

TensorView types:

    struct TensorView[T, Shape: (int...), Layout: TensorLayout]:
        data: &[T]           # Borrowed slice
        strides: (int...)    # For non-contiguous views
        
        fn is_contiguous() -> bool:
            # Check if view is contiguous in memory

Integration with Performance Primitives
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Tensors compose naturally with Pyrite's existing features using parameter 
closures (zero-cost):

    # SIMD operations on tensors
    fn scale_tensor[Rows: int, Cols: int](
        data: &mut Tensor[f32, (Rows, Cols), RowMajor],
        factor: f32
    ):
        # Parameter closure (fn[...]) is inlined into SIMD loop
        algorithm.vectorize[width=auto](Rows * Cols, fn[i: int]:
            data.data[i] *= factor
        )
    
    # Cache-aware matrix multiply
    fn matmul[M: int, N: int, K: int](
        a: &Tensor[f32, (M, K), RowMajor],
        b: &Tensor[f32, (K, N), ColMajor]
    ) -> Tensor[f32, (M, N), RowMajor]:
        var result = Tensor[M, N]::zeros()
        
        # Parameter closure (fn[...]) inlined into tiling loop (zero-cost)
        algorithm.tile[block_size=64](M, N, fn[i_block: int, j_block: int]:
            # Process 64×64 tiles (cache-friendly)
            for i in i_block..min(i_block + 64, M):
                for j in j_block..min(j_block + 64, N):
                    result[(i, j)] = dot_product(a.row(i), b.col(j))
        )
        
        return result

Dynamic-Size Tensors
~~~~~~~~~~~~~~~~~~~~

For cases where sizes aren't known at compile time:

    struct DynTensor[T, Rank: int, Layout: TensorLayout]:
        data: List[T]        # Heap-allocated
        shape: [int; Rank]   # Runtime shape
        strides: [int; Rank] # Runtime strides

Type Safety
~~~~~~~~~~~

Compile-time checking prevents common numeric code bugs:

    let a = Tensor[f32, (10, 20), RowMajor]::zeros()
    let b = Tensor[f32, (20, 30), RowMajor]::zeros()
    let c = matmul(&a, &b)  # OK: (10,20) × (20,30) → (10,30)
    
    let d = Tensor[f32, (15, 25), RowMajor]::zeros()
    # let e = matmul(&a, &d)  # ERROR: incompatible shapes

Why This Matters
~~~~~~~~~~~~~~~~

Pyrite's Tensor fills the gap between "write loops" and "use heavyweight ML 
framework":

  • Compile-time shape checking prevents dimension mismatch bugs
  • Explicit layout control (row-major vs col-major) for optimal cache usage
  • Zero-cost slicing through borrowing semantics
  • Composes with existing performance tools (SIMD, tiling, parallelization)
  • No runtime overhead (fixed-size tensors are stack-allocated)

This makes Pyrite credible for numerical computing without becoming "yet another 
ML framework." Provide the foundation; let libraries build on top.

Implementation: Stable Release (after SIMD and algorithmic helpers are stable)

## 9.12 SIMD and Vectorization (Stable Release)

For performance-critical numerical code, Pyrite provides explicit SIMD 
(Single Instruction, Multiple Data) support through the std::simd module. 
This is opt-in and explicit - Pyrite does not auto-vectorize, ensuring 
predictable performance.

Design Philosophy
~~~~~~~~~~~~~~~~~

SIMD in Pyrite follows the language's core principles:

  • **Explicit, not implicit:** You write SIMD code explicitly
  • **Portable, not platform-specific:** APIs work across architectures
  • **Zero-cost:** Compiles to native vector instructions
  • **Type-safe:** Compiler prevents SIMD misuse
  • **Teachable:** Clear syntax and error messages

SIMD Types
~~~~~~~~~~

The std::simd module provides generic vector types:

    import std::simd
    
    # Portable vector types
    let v1 = simd::Vec[f32, 4]::new([1.0, 2.0, 3.0, 4.0])  # 4-wide f32 vector
    let v2 = simd::Vec[f32, 4]::new([5.0, 6.0, 7.0, 8.0])
    
    # Element-wise operations
    let sum = v1 + v2           # [6.0, 8.0, 10.0, 12.0]
    let product = v1 * v2       # [5.0, 12.0, 21.0, 32.0]

Platform-Specific Width Detection
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Use compile-time introspection to choose optimal SIMD width:

    import std::simd
    
    fn process_array(data: &[f32]):
        # Choose width based on CPU capabilities
        const WIDTH = simd::preferred_width[f32]()  # 4, 8, or 16
        
        # Process in SIMD chunks
        let chunks = data.chunks(WIDTH)
        for chunk in chunks:
            let vec = simd::Vec[f32, WIDTH]::load(chunk)
            # ... SIMD operations ...
            vec.store(chunk)

Common SIMD Operations
~~~~~~~~~~~~~~~~~~~~~~

    import std::simd
    
    fn dot_product[N: int](a: [f32; N], b: [f32; N]) -> f32:
        # Compile-time SIMD width selection
        const WIDTH = simd::preferred_width[f32]()
        
        var sum = 0.0
        var i = 0
        
        # Process SIMD chunks
        while i + WIDTH <= N:
            let va = simd::Vec[f32, WIDTH]::load(&a[i])
            let vb = simd::Vec[f32, WIDTH]::load(&b[i])
            let prod = va * vb
            sum += prod.horizontal_sum()
            i += WIDTH
        
        # Process remainder scalar
        while i < N:
            sum += a[i] * b[i]
            i += 1
        
        return sum

Integration with Compile-Time Parameterization
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

SIMD combines naturally with Pyrite's compile-time parameters:

    fn matrix_multiply[Rows: int, Cols: int, Width: int](
        a: &Matrix[Rows, Cols],
        b: &Matrix[Cols, Width]
    ) -> Matrix[Rows, Width]:
        # All dimensions known at compile time
        # Compiler can unroll loops and use SIMD
        
        const SIMD_WIDTH = simd::preferred_width[f32]()
        var result = Matrix[Rows, Width]::zero()
        
        for i in 0..Rows:
            for j in 0..Width:
                # SIMD inner product if Cols >= SIMD_WIDTH
                if Cols >= SIMD_WIDTH:
                    result[i, j] = simd_dot_product(&a[i], &b.col(j))
                else:
                    result[i, j] = scalar_dot_product(&a[i], &b.col(j))
        
        return result

Why Explicit SIMD?
~~~~~~~~~~~~~~~~~~

Pyrite does NOT auto-vectorize user code because:

1. **Predictability:** Developers know exactly which code uses SIMD
2. **Cost transparency:** SIMD is a deliberate performance choice
3. **Portability:** Explicit SIMD works across compilers and platforms
4. **Debugging:** SIMD bugs are isolated to SIMD-marked code
5. **Teaching:** Developers learn when and why to use SIMD

Auto-vectorization is "magic" that sometimes works and sometimes doesn't, 
depending on compiler whims. Explicit SIMD is a contract: you write vector 
code, you get vector instructions.

SIMD in Standard Library Implementation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

While user code requires explicit SIMD, the standard library MAY use SIMD 
internally for implementation efficiency:

  • Numeric operations (integer/float arithmetic) can use SIMD primitives
  • String operations (search, compare) may use vector instructions
  • Collection operations (sorting, scanning) can leverage SIMD

Key principle: **User-facing API remains explicit, internal implementation can 
optimize**

Example:

    # User code: explicit about SIMD
    let result = algorithm.vectorize[width=8](data.len(), fn[i: int]:
        data[i] *= 2.0
    )
    
    # Stdlib internals: may use SIMD for implementation
    impl String:
        fn contains(&self, pattern: &str) -> bool:
            # Internal: may use SIMD for byte scanning
            # External: API doesn't promise SIMD (implementation detail)

Documentation clarifies:

    """
    String::contains - Searches for substring
    
    Implementation: Uses SIMD byte scanning on supported platforms
    Fallback: Scalar search on platforms without SIMD
    
    Performance: O(n*m) worst case, O(n) typical with SIMD
    
    This is an implementation detail. The API contract is:
      • Returns bool indicating presence
      • No allocation
      • No side effects
    
    Run 'quarry explain-type String' to see platform-specific implementation
    """

This approach:
  • Keeps user code explicit (no surprise SIMD in user functions)
  • Allows stdlib to be fast by default (internal SIMD for efficiency)
  • Maintains cost transparency (quarry explain-type shows implementation choices)
  • Teaches that "explicit for control, implicit for convenience" applies at the 
    right boundary (stdlib internals vs user code)

The distinction: **User code = explicit SIMD, Stdlib internals = may use SIMD**

This aligns with Mojo's "SIMD is fundamental" philosophy while maintaining 
Pyrite's "no surprises" surface API. Users get fast stdlib implementations 
without needing to understand SIMD until they're ready to optimize their own 
hot paths.

Attributes for SIMD Code
~~~~~~~~~~~~~~~~~~~~~~~~

Mark functions that should use SIMD:

    @simd(width=4)
    fn process_floats(data: &mut [f32]):
        # Compiler ensures SIMD instructions are generated
        # Errors if SIMD width not achievable

Compare with non-SIMD:

    fn process_floats_scalar(data: &mut [f32]):
        # Regular scalar code
        # No SIMD expectations

Platform Support
~~~~~~~~~~~~~~~~

SIMD support is tiered:

  • **Tier 1:** x86_64 (SSE2/AVX2/AVX-512), ARM64 (NEON)
  • **Tier 2:** ARM32 (NEON), RISC-V (vector extension)
  • **Fallback:** Scalar emulation on unsupported platforms

The std::simd API is the same across all platforms - only the generated 
instructions differ.

CPU Multi-Versioning (Stable Release)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For shipping single binaries that run optimally across diverse hardware, Pyrite 
provides CPU multi-versioning with automatic runtime dispatch for SIMD and other 
CPU features:

SIMD Multi-Versioning
~~~~~~~~~~~~~~~~~~~~~

    @multi_version(
        baseline="sse2",           # Minimum requirement (runs everywhere)
        targets=["avx2", "avx512"] # Optimized variants
    )
    fn process_pixels(data: &mut [f32]):
        # Compiler generates 3 versions:
        # 1. process_pixels_sse2   - baseline (4-wide SIMD)
        # 2. process_pixels_avx2   - AVX2 (8-wide SIMD)
        # 3. process_pixels_avx512 - AVX-512 (16-wide SIMD)
        
        # Write code once using portable SIMD
        # Parameter closure (fn[...]) inlined per version
        const WIDTH = simd::preferred_width[f32]()
        algorithm.vectorize[width=WIDTH](data.len(), fn[i: int]:
            data[i] = data[i].sqrt() * 2.0
        )

General CPU Feature Multi-Versioning
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Beyond SIMD, @multi_version supports targeting arbitrary CPU feature sets for 
maximum performance across diverse hardware:

    @multi_version(
        baseline="x86-64",           # Core x86-64 ISA
        targets=[
            "x86-64-v2",             # +SSE4.2, +POPCNT
            "x86-64-v3",             # +AVX2, +BMI2, +FMA
            "x86-64-v4"              # +AVX-512
        ]
    )
    fn hash_data(data: &[u8]) -> u64:
        # Compiler generates 4 versions using different instruction sets
        # v2: Uses POPCNT, CRC32 intrinsics
        # v3: Uses BMI2 (PDEP/PEXT), FMA for polynomial hashing
        # v4: Uses AVX-512 for vectorized hashing
        
        var hash: u64 = 0
        for byte in data:
            hash = hash.wrapping_mul(31).wrapping_add(byte as u64)
        return hash

Feature-specific optimizations:

    @multi_version(
        baseline="generic",
        targets=[
            "+popcnt",               # Population count instruction
            "+bmi2",                 # Bit manipulation instructions 2
            "+aes"                   # AES-NI hardware acceleration
        ]
    )
    fn count_bits(data: &[u64]) -> usize:
        var count = 0
        for word in data:
            count += word.count_ones()  # Uses POPCNT on +popcnt target
        return count

Cross-architecture support:

    @multi_version(
        baseline="generic",
        targets=[
            "x86-64-v3",             # Intel/AMD modern
            "aarch64+neon",          # ARM64 with NEON
            "aarch64+sve",           # ARM64 with SVE
            "riscv64+v"              # RISC-V with vector extension
        ]
    )
    fn accelerated_compute(data: &mut [f32]):
        # Single code, multiple architectures
        # Compiler selects target based on runtime CPU detection

At program startup, runtime dispatcher detects CPU features and selects best 
version. Subsequent calls use the fast path directly (cached function pointer).

How it works:

1. **Compile time:** Compiler generates multiple versions
   - Each version compiled with different target-feature flags
   - Baseline version always generated (guaranteed to run)
   - Optimized versions use advanced instructions

2. **Startup time:** Runtime CPU feature detection (one-time cost)
   - Check CPUID on x86_64
   - Check hwcaps on ARM
   - Build dispatch table (function pointer per multi-versioned function)

3. **Runtime:** First call goes through dispatcher
   - Dispatcher selects best available version
   - Updates function pointer to direct call
   - Subsequent calls are direct (zero overhead)

Example generated code (conceptual):

    # Generated by compiler
    fn process_pixels_sse2(data: &mut [f32]):
        # Use SSE2 instructions (4-wide)
    
    fn process_pixels_avx2(data: &mut [f32]):
        # Use AVX2 instructions (8-wide)
    
    fn process_pixels_avx512(data: &mut [f32]):
        # Use AVX-512 instructions (16-wide)
    
    # Runtime dispatcher (called once at startup)
    static mut PROCESS_PIXELS_PTR: fn(&mut [f32]) = process_pixels_dispatch
    
    fn process_pixels_dispatch(data: &mut [f32]):
        # CPU feature detection
        if cpu_has_avx512():
            PROCESS_PIXELS_PTR = process_pixels_avx512
        elif cpu_has_avx2():
            PROCESS_PIXELS_PTR = process_pixels_avx2
        else:
            PROCESS_PIXELS_PTR = process_pixels_sse2
        
        # Tail call to selected version
        PROCESS_PIXELS_PTR(data)
    
    # Public API (always calls through pointer)
    fn process_pixels(data: &mut [f32]):
        PROCESS_PIXELS_PTR(data)

Cross-architecture support:

    @multi_version(
        baseline="generic",           # Scalar fallback
        targets=["neon", "sve"]       # ARM variants
    )
    fn compute(data: &mut [f32]):
        # Works on ARM64 with NEON/SVE detection

Benefits:
  • **Ship once, run fast everywhere:** One binary for all CPUs
  • **No user configuration:** Automatic at runtime
  • **Predictable performance:** Always uses best available instructions
  • **Gradual adoption:** Old CPUs run baseline, new CPUs get speedup
  • **Zero cost if not used:** No overhead for non-multi-versioned code

Performance impact:
  • Baseline (SSE2): 4-wide SIMD
  • AVX2: 8-wide = 2x faster
  • AVX-512: 16-wide = 4x faster
  • Typical real-world: 2-3x speedup on modern CPUs vs baseline

Use cases:
  • Image/video processing (run fast on desktop and laptop)
  • Scientific computing (support diverse HPC hardware)
  • Game engines (optimal on high-end and low-end machines)
  • Cryptography (constant-time algorithms with best instructions)

Cost transparency:
  • quarry cost shows: "3 versions generated (+10% binary size)"
  • Compiler warns if variants are identical: "AVX2 and AVX-512 generate same code"
  • quarry explain shows dispatch cost: "One-time <5μs, amortized zero"

Teaching path:
  1. **Intermediate:** Write portable SIMD with preferred_width
  2. **Advanced:** Add @multi_version for production deployment
  3. **Expert:** Profile across targets, tune per-variant code

Integration with compilation:

    quarry build --release --multi-version
    # Generates all target variants
    # Binary contains: _sse2, _avx2, _avx512 versions + dispatcher

Limitations:
  • Only for performance-critical functions (not everything)
  • Binary size increases (N versions × function size)
  • Startup cost for CPU detection (amortized over runtime)

This is a **Stable Release flagship feature** that differentiates Pyrite in deployment 
scenarios. No other systems language makes "fast everywhere" this easy.

Learning Path
~~~~~~~~~~~~~

SIMD is introduced late in the learning curve:

1. **Beginner:** Write scalar code, learn ownership
   
   for i in 0..data.len():
       data[i] *= 2.0

2. **Intermediate:** Use algorithmic helpers (parameter closures)
   
   algorithm.vectorize[width=auto](data.len(), fn[i: int]:
       data[i] *= 2.0
   )
   
   "Write scalar logic in fn[...], get SIMD automatically"

3. **Advanced:** Learn explicit SIMD for critical loops
   
   const WIDTH = simd::preferred_width[f32]()
   while i + WIDTH <= len:
       let vec = simd::Vec[f32, WIDTH]::load(&data[i])
       ...

4. **Expert:** Write SIMD libraries with compile-time specialization
   
   fn kernel[Width: int](data: &mut [f32]):
       # Specialized versions per Width
       ...

The parameter closure model (fn[...]) provides the bridge between scalar code 
(beginner-friendly) and SIMD code (expert-level). Beginners write scalar logic 
in parameter closures, get SIMD performance automatically through vectorize.

SIMD is opt-in performance for those who need it, not a requirement for 
everyday code. Parameter closures make the "opt-in" ergonomic enough for 
intermediate developers.

Algorithmic Helpers: Ergonomic Entry Points
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

While explicit SIMD (std::simd) provides full control, most developers benefit 
from higher-level helpers that compile to optimal SIMD code. The std::algorithm 
module provides ergonomic entry points inspired by Mojo's algorithmic primitives:

vectorize - Automatic SIMD Loop Generation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The vectorize helper automatically generates SIMD loops from scalar operations 
using parameter closures (compile-time, zero-cost):

    import std::algorithm
    
    fn scale_array(data: &mut [f32], factor: f32):
        # High-level: describe what to do per element
        # Parameter closure (fn[...]) is inlined, zero allocation
        algorithm.vectorize[width=auto](data.len(), fn[i: int]:
            data[i] = data[i] * factor
        )
    
    # Compiler generates:
    # 1. SIMD loop for aligned chunks (Vec[f32, WIDTH])
    # 2. Scalar loop for remainder elements
    # 3. Optimal width selection based on platform
    # 4. Closure body inlined directly (no function call)

Parameters:
  • width=auto: Compiler chooses optimal SIMD width (4, 8, or 16)
  • width=N: Force specific width (e.g., width=8 for AVX)
  • unroll=N: Loop unrolling factor (default: auto)

Example with manual width:

    # Force 8-wide SIMD (AVX2)
    # Parameter closure: fn[i: int] with square brackets
    algorithm.vectorize[width=8](pixels.len(), fn[i: int]:
        pixels[i] = clamp(pixels[i], 0.0, 1.0)
    )

Generated code (conceptual):

    const WIDTH = 8
    var i = 0
    
    # SIMD loop
    while i + WIDTH <= pixels.len():
        let vec = simd::Vec[f32, 8]::load(&pixels[i])
        let clamped = vec.clamp(0.0, 1.0)
        clamped.store(&mut pixels[i])
        i += WIDTH
    
    # Scalar remainder
    while i < pixels.len():
        pixels[i] = clamp(pixels[i], 0.0, 1.0)
        i += 1

Benefits:
  • Write scalar logic, get SIMD performance
  • Handles alignment and remainder automatically
  • Compiler can optimize based on array length (compile-time if known)
  • Still explicit (vectorize call is visible, not hidden)

parallelize - Structured Parallel Execution
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The parallelize helper provides safe, structured parallelism using parameter 
closures (compile-time, zero-allocation):

    import std::algorithm
    
    fn process_image_rows(image: &mut Image):
        # Parallel execution with automatic work distribution
        # Parameter closure (fn[...]) is replicated per thread, zero allocation
        algorithm.parallelize(image.height(), fn[row: int]:
            process_row(&mut image[row])
        )

Parameters:
  • workers=auto: Use all available CPU cores (default)
  • workers=N: Use exactly N threads
  • chunk_size=auto: Optimal work distribution (default)
  • chunk_size=N: Process N items per thread

Example with custom parameters:

    # Use 4 threads, process 100 items per chunk
    # Parameter closure is inlined into each thread's work loop
    algorithm.parallelize[workers=4, chunk_size=100](
        data.len(),
        fn[i: int]:
            data[i] = expensive_computation(data[i])
    )

Safety guarantees:
  • Parameter closure body must be Send (checked at compile time)
  • No data races (ownership rules enforced on captures)
  • Structured concurrency (waits for all threads before returning)
  • Exceptions in worker threads are caught and propagated
  • Zero allocation for closure itself (parameter closure is inlined)

Generated code (conceptual):

    let num_workers = 4
    let chunk_size = 100
    let channel = Channel[Result[(), Error]].new()
    
    for worker_id in 0..num_workers:
        Thread.spawn(fn():
            let start = worker_id * chunk_size
            let end = min(start + chunk_size, data.len())
            for i in start..end:
                channel.send(try work_fn(i))
        )
    
    # Wait for all workers, propagate errors
    for _ in 0..num_workers:
        channel.receive()?

Combined: Parallel + SIMD
~~~~~~~~~~~~~~~~~~~~~~~~~~

Algorithmic helpers compose naturally using parameter closures (zero allocation):

    fn process_large_dataset(data: &mut [f32]):
        # Parallel execution across cores
        # Both closures are parameter closures (compile-time, inlined)
        algorithm.parallelize(data.len() / 1000, fn[chunk_id: int]:
            let start = chunk_id * 1000
            let end = start + 1000
            let chunk = &mut data[start..end]
            
            # SIMD within each parallel chunk
            algorithm.vectorize[width=auto](chunk.len(), fn[i: int]:
                chunk[i] = chunk[i].sqrt() * 2.0
            )
        )

This gives both:
  • Parallelism across CPU cores (thread-level)
  • Vectorization within each core (SIMD-level)
  • **Zero allocation:** Both closures are parameter closures (inlined)
  • **Verifiable:** Works with `quarry build --no-alloc`

Result: Maximum hardware utilization with clear, maintainable code and proven 
zero-cost abstraction.

tile - Cache-Aware Blocking
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The tile helper enables cache-friendly access patterns by processing data in 
blocks that fit in CPU cache (inspired by Mojo's tiling primitives), using 
parameter closures for zero-cost abstraction:

    import std::algorithm
    
    fn matrix_multiply(a: &Matrix, b: &Matrix) -> Matrix:
        const TILE_SIZE = 64  # Fits in L1 cache
        var result = Matrix::zeros(a.rows, b.cols)
        
        # Process in cache-friendly tiles
        # Parameter closure (fn[...]) inlined into tiling loop
        algorithm.tile[block_size=TILE_SIZE](
            a.rows, b.cols,
            fn[i_block: int, j_block: int]:
                # This 64x64 block stays in L1 cache
                for i in i_block..min(i_block + TILE_SIZE, a.rows):
                    for j in j_block..min(j_block + TILE_SIZE, b.cols):
                        result[i, j] = dot_product(&a[i], &b.col(j))
        )
        
        return result

Parameters:
  • block_size=N: Tile size (typically 32-128 for L1 cache)
  • block_size=auto: Compiler chooses based on target cache size

Why tiling matters:
  • L1 cache: ~50 KB, 4 cycles access
  • L2 cache: ~256 KB, 12 cycles access
  • L3 cache: ~8 MB, 40 cycles access
  • Main RAM: Unlimited, 200+ cycles access

Processing 64x64 tiles (32 KB for f64) keeps data in L1 = 50x faster than RAM.

Generated code (conceptual):

    const BLOCK = 64
    for i_block in range(0, rows, BLOCK):
        for j_block in range(0, cols, BLOCK):
            # Inner loops operate on BLOCK×BLOCK tile
            for i in i_block..min(i_block + BLOCK, rows):
                for j in j_block..min(j_block + BLOCK, cols):
                    work_fn(i, j)

Common use cases:
  • Matrix operations (multiply, transpose, convolution)
  • Image processing (filters, transforms)
  • Stencil computations (fluid dynamics, heat transfer)
  • Any algorithm with O(n²) or O(n³) data access

Integration with profiling:
  • quarry perf shows cache misses per function
  • quarry tune suggests: "Add tiling to reduce cache misses"
  • Estimates improvement: "80% cache miss rate → 5% with tile[64]"

Teaching path:
  1. **Beginner:** Write nested loops, profile shows slow
  2. **Intermediate:** Learn cache hierarchy, apply tile
  3. **Advanced:** Tune block_size based on target CPU
  4. **Expert:** Combine tile + vectorize + parallelize

Example: Matrix multiply speedup
  • Naive: 100% cache misses, 45 seconds
  • Tiled [64]: 5% cache misses, 3 seconds (15x faster)
  • Tiled + SIMD: 1 second (45x faster)
  • Tiled + SIMD + Parallel: 0.2 seconds (225x faster)

The tile helper is the missing piece between "scalar loops" and "production 
performance" for numeric code. Stable Release feature.

Future: Additional Loop Transforms
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Based on real-world demand, Stable Release may add:

  • algorithm.unswitch - Move loop-invariant conditionals outside loops
  • algorithm.fuse - Merge adjacent loops to reduce overhead
  • algorithm.split - Split loops for better parallelization
  • algorithm.peel - Peel first/last iterations for alignment

These follow the same philosophy: explicit, composable, inspectable. Only added 
if user feedback demonstrates need. Avoid premature complexity.

Teaching Path for Performance
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The algorithmic helpers provide a gentle introduction to high-performance code:

1. **Beginner:** Write scalar loops
   
   for i in 0..data.len():
       data[i] = data[i] * 2.0

2. **Intermediate:** Add vectorize for SIMD
   
   # Parameter closure: fn[i: int] with square brackets (zero-cost)
   algorithm.vectorize[width=auto](data.len(), fn[i: int]:
       data[i] = data[i] * 2.0
   )

3. **Advanced:** Add parallelize for multi-core
   
   # Both parameter closures (nested, still zero allocation)
   algorithm.parallelize(chunks, fn[chunk_id: int]:
       algorithm.vectorize[...](fn[i: int]: ...)
   )

4. **Expert:** Drop to explicit std::simd for fine control
   
   const WIDTH = simd::preferred_width[f32]()
   while i + WIDTH <= len:
       let vec = simd::Vec[f32, WIDTH]::load(&data[i])
       ...

Each step is a natural progression, and the helpers desugar to explicit code 
that can be inspected (quarry expand can show generated code). The parameter 
closure syntax (fn[...]) signals "this is inlined, zero-cost" while runtime 
closures (fn(...)) signal "this may allocate, has runtime representation."

The teaching path for closures:

1. **Week 1-2 (Use without understanding):**
   Just write the body, don't think about closure mechanics
   
       algorithm.vectorize[width=auto](data.len(), fn[i: int]:
           data[i] *= 2.0
       )

2. **Week 3-4 (Learn runtime closures):**
   Understand closures as values for callbacks
   
       let filter = fn(x: int) -> bool: x > 10
       Thread.spawn(fn(): background_work())

3. **Week 5+ (Understand the distinction):**
   Learn that fn[...] is compile-time (free), fn(...) is runtime (may cost)
   
       # Zero-cost (parameter)
       algorithm.vectorize[width=8](n, fn[i: int]: ...)
       
       # May allocate (runtime)
       Thread.spawn(fn(): ...)
   
   See the difference in quarry cost output

4. **Expert (Choose appropriately):**
   Use parameter closures for performance-critical hot paths
   Use runtime closures when flexibility/escape needed

Autotuning: Machine-Specific Optimization
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For performance-critical code, optimal parameters (SIMD width, tile size, unroll 
factors) vary by hardware. Pyrite provides autotuning as a TOOL that generates 
code, not runtime magic.

Design Philosophy
~~~~~~~~~~~~~~~~~

Autotuning in Pyrite is explicit and transparent:
  • NOT runtime adaptation (no overhead)
  • NOT hidden compiler heuristics (no magic)
  • YES codegen tool that outputs constants
  • YES checked-in configuration (reproducible)

This avoids the pitfalls that caused Mojo to deprecate their autotuning system--
Pyrite's approach has zero runtime cost and is fully inspectable.

Command Usage
~~~~~~~~~~~~~

    quarry autotune                     # Tune all autotunable functions
    quarry autotune matrix_multiply     # Tune specific function
    quarry autotune --profile=release   # Tune for release optimizations
    quarry autotune --target=avx512     # Tune for specific CPU features

How It Works
~~~~~~~~~~~~

1. **Identify tunable parameters:** Functions marked @autotune or using 
   algorithm helpers with parameter placeholders

2. **Generate variants:** Compile multiple versions with different parameters

3. **Benchmark:** Run microbenchmarks on target hardware

4. **Select optimal:** Choose parameters with best performance

5. **Generate code:** Output tuned constants to checked-in file

Example: Tuning Matrix Multiply
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Source code with tunable parameters:

    @autotune(params=["TILE_SIZE", "SIMD_WIDTH", "UNROLL_FACTOR"])
    fn matrix_multiply[M: int, N: int, K: int](
        a: &Matrix[M, K],
        b: &Matrix[K, N]
    ) -> Matrix[M, N]:
        # Use tuned parameters (will be generated)
        const TILE_SIZE = tuned::MATRIX_MULTIPLY_TILE_SIZE
        const SIMD_WIDTH = tuned::MATRIX_MULTIPLY_SIMD_WIDTH
        const UNROLL_FACTOR = tuned::MATRIX_MULTIPLY_UNROLL
        
        var result = Matrix[M, N]::zeros()
        
        # Parameter closures (fn[...]) are inlined and unrolled
        algorithm.tile[block_size=TILE_SIZE](M, N, fn[i: int, j: int]:
            algorithm.vectorize[width=SIMD_WIDTH, unroll=UNROLL_FACTOR](
                K, fn[k: int]:
                    result[i, j] += a[i, k] * b[k, j]
            )
        )
        
        return result

Run autotuner:

    $ quarry autotune matrix_multiply
    
    Autotuning: matrix_multiply
    ════════════════════════════════════
    
    Detected hardware:
      • CPU: Intel Core i9-12900K
      • L1 cache: 48 KB per core
      • L2 cache: 1.25 MB per core
      • L3 cache: 30 MB shared
      • SIMD: AVX2 (8-wide f32), AVX-512 (16-wide f32)
    
    Testing parameter combinations:
      • TILE_SIZE: [32, 64, 128, 256]
      • SIMD_WIDTH: [4, 8, 16]
      • UNROLL_FACTOR: [1, 2, 4, 8]
      • Total: 48 combinations
    
    Benchmarking (matrix size 1024×1024):
    
      [████████████████░░░░] 80% (38/48 combinations tested)
      
      Best so far:
        TILE_SIZE=64, SIMD_WIDTH=8, UNROLL_FACTOR=4
        Time: 234ms (baseline: 892ms, 3.8x faster)
    
    ✓ Optimal parameters found:
    
      TILE_SIZE = 64
        • Fits in L1 cache (32 KB for f32)
        • Minimizes cache misses
      
      SIMD_WIDTH = 8
        • AVX2 available (8-wide f32 vectors)
        • Better than AVX-512 for this workload (overhead not justified)
      
      UNROLL_FACTOR = 4
        • Balance: instruction-level parallelism vs code size
        • Diminishing returns beyond 4
    
    Performance:
      • Baseline (naive): 892ms
      • Tuned: 234ms
      • Speedup: 3.81x
    
    Generated: src/generated/tuned_params.pyr

Generated File
~~~~~~~~~~~~~~

Autotuner outputs human-readable, checked-in constants:

    # src/generated/tuned_params.pyr
    # AUTO-GENERATED by 'quarry autotune' on 2025-12-18
    # Hardware: Intel Core i9-12900K
    # DO NOT EDIT - Regenerate with 'quarry autotune'
    
    """
    Tuned parameters for optimal performance on target hardware.
    
    Benchmark results:
      • matrix_multiply: 234ms (3.81x faster than baseline)
      • Tested: 48 parameter combinations
      • Hardware: i9-12900K, AVX2, 48 KB L1
    """
    
    # Matrix multiplication tuning
    const MATRIX_MULTIPLY_TILE_SIZE: int = 64
    const MATRIX_MULTIPLY_SIMD_WIDTH: int = 8
    const MATRIX_MULTIPLY_UNROLL: int = 4
    
    # Image processing tuning
    const BLUR_KERNEL_TILE_SIZE: int = 128
    const BLUR_SIMD_WIDTH: int = 8
    
    # ... more tuned constants ...

Application code imports these:

    import generated::tuned
    
    fn matrix_multiply[M: int, N: int, K: int](...):
        const TILE_SIZE = tuned::MATRIX_MULTIPLY_TILE_SIZE  # 64
        # ... use tuned constant ...

Per-Platform Tuning
~~~~~~~~~~~~~~~~~~~

Different platforms need different parameters:

    # Tune for multiple targets
    quarry autotune --target=x86_64-linux
    quarry autotune --target=aarch64-linux
    quarry autotune --target=riscv64-linux

Generated files:

    src/generated/tuned_x86_64.pyr
    src/generated/tuned_aarch64.pyr
    src/generated/tuned_riscv64.pyr

Conditional compilation selects appropriate file:

    @cfg(target = "x86_64")
    import generated::tuned_x86_64 as tuned
    
    @cfg(target = "aarch64")
    import generated::tuned_aarch64 as tuned

Benefits of Tool-Based Autotuning
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Compared to runtime autotuning (Mojo's original approach, now deprecated):

Pyrite's tool-based approach:
  ✓ Zero runtime cost (constants compiled in)
  ✓ Fully inspectable (generated file is readable)
  ✓ Reproducible (checked-in file, version controlled)
  ✓ No hidden behavior (explicit import of tuned::*)
  ✓ CI-friendly (deterministic builds)
  ✓ Cross-compilation safe (tune per target)

Runtime autotuning pitfalls (why Mojo abandoned it):
  ✗ Runtime overhead (measure and adapt on every run)
  ✗ Non-deterministic (results vary by machine)
  ✗ Hidden behavior (parameters chosen invisibly)
  ✗ CI complexity (different results on different machines)
  ✗ Debugging nightmare (works on my machine!)

When to Use Autotuning
~~~~~~~~~~~~~~~~~~~~~~~

Use quarry autotune for:
  • Performance-critical kernels (hot paths)
  • Numeric code with hardware-dependent optimal parameters
  • Code shipping to diverse hardware (tune per target)
  • Libraries where 10-50% improvement justifies tuning effort

Don't use for:
  • Non-critical code (manual tuning good enough)
  • Code that's not performance-bottleneck
  • First optimization pass (profile first, tune later)

Workflow Integration
~~~~~~~~~~~~~~~~~~~~

Autotuning fits naturally into development:

1. **Develop:** Write code with algorithm.tile[block_size=64]
2. **Profile:** quarry perf shows it's a hot spot
3. **Autotune:** quarry autotune finds TILE_SIZE=128 is 20% faster
4. **Apply:** Import tuned constants, regenerate for production hardware
5. **CI:** Run quarry autotune in CI to detect performance regressions

Example production workflow:

    # Development: Use reasonable defaults
    const TILE_SIZE = 64
    
    # Production: Use tuned values
    const TILE_SIZE = tuned::MATRIX_MULTIPLY_TILE_SIZE
    
    # CI: Regenerate and verify
    quarry autotune --check  # Fail if tuned values are stale

Cost Transparency
~~~~~~~~~~~~~~~~~

Autotuning maintains Pyrite's explicitness:

    $ quarry cost --show-tuning
    
    Tuned Parameters in Use:
    ════════════════════════
    
    src/math.py:234 - matrix_multiply
      • TILE_SIZE: 64 (from tuned::MATRIX_MULTIPLY_TILE_SIZE)
      • Source: src/generated/tuned_params.pyr:15
      • Tuned on: 2025-12-18 (Intel i9-12900K)
      • Speedup vs baseline: 3.81x
    
    ⚠️  Warning: Tuned for x86_64, running on aarch64
        Performance may be suboptimal
        Run 'quarry autotune --target=aarch64' to re-tune

This makes tuning decisions visible and auditable - no hidden magic.

Why This Approach Wins
~~~~~~~~~~~~~~~~~~~~~~~

Pyrite's tool-based autotuning provides:
  • Mojo's performance benefits (tuned parameters for hardware)
  • None of Mojo's runtime overhead (zero cost at runtime)
  • Full transparency (generated file is version controlled)
  • Reproducible builds (CI and prod use same tuned values)

This is "autotuning done right" - as a build tool, not language semantics.

CI Verification and Perf.lock Integration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Autotuning integrates with the performance lockfile (Perf.lock) to prevent 
regressions and ensure tuned parameters remain optimal:

    quarry autotune --verify                # Check tuned params vs current hardware
    quarry autotune --check                 # Fail CI if params are stale
    quarry autotune --update-lockfile       # Update Perf.lock with new params

Workflow with performance lockfile:

1. **Initial tuning:** Generate optimal parameters
   
       $ quarry autotune
       Generated: src/generated/tuned_params.pyr
       
       Optimal parameters found:
         • MATRIX_MULTIPLY_TILE_SIZE = 64
         • MATRIX_MULTIPLY_SIMD_WIDTH = 8
         • Speedup: 3.81x vs baseline

2. **Commit to version control:** Tuned parameters become reproducible baseline
   
       $ git add src/generated/tuned_params.pyr Perf.lock
       $ git commit --m "Add autotuned parameters for matrix_multiply"

3. **CI verification:** Ensure parameters remain valid on deployment hardware
   
       $ quarry autotune --verify
       
       Verifying tuned parameters on current hardware...
       
       ✓ MATRIX_MULTIPLY_TILE_SIZE=64 validated (64 is still optimal)
       ✓ MATRIX_MULTIPLY_SIMD_WIDTH=8 validated (AVX2 available)
       ✓ Performance matches baseline: 234ms (3.81x)
       
       All tuned parameters remain optimal

4. **Detect staleness:** Warn if hardware changed significantly
   
       $ quarry autotune --verify
       
       ⚠️  WARNING: Tuned parameters may be suboptimal
       
       Hardware mismatch:
         • Tuned for: Intel i9-12900K (AVX2, 48KB L1)
         • Running on: AMD Ryzen 9 7950X (AVX-512, 32KB L1)
       
       Benchmark results:
         • matrix_multiply: 189ms (was 234ms on tuned hardware)
         • Speedup vs baseline: 4.72x (better than original!)
       
       Recommendation:
         Hardware improved - consider re-tuning:
           quarry autotune --update-lockfile
         
         Expected improvements:
           • SIMD_WIDTH: 8 → 16 (AVX-512 available)
           • Potential: 5.5x speedup (vs current 4.72x)

Integration with Perf.lock Format
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Autotuned parameters are recorded in Perf.lock alongside performance baselines:

    # Perf.lock (YAML format)
    version: "1.0"
    generated: "2025-12-18T10:30:00Z"
    build: "--release --lto=thin"
    platform: "x86_64-linux (Intel i9-12900K)"
    
    autotuned_parameters:
      matrix_multiply:
        tile_size: 64
        simd_width: 8
        unroll_factor: 4
        benchmark_time_ms: 234
        speedup_vs_baseline: 3.81
        tested_combinations: 48
        tuning_date: "2025-12-18T10:30:00Z"
      
      blur_kernel:
        tile_size: 128
        simd_width: 8
        benchmark_time_ms: 89
        speedup_vs_baseline: 2.34
        tested_combinations: 32
    
    hot_functions:
      - name: "process_data"
        time_ms: 1247
        uses_autotuned: true
        autotuned_params: ["matrix_multiply"]
        # ... rest of Perf.lock content ...

CI Pipeline Example
~~~~~~~~~~~~~~~~~~~

Complete CI workflow combining autotuning verification with performance regression 
detection:

    # .github/workflows/ci.yml
    name: Performance CI
    
    jobs:
      performance:
        steps:
          - name: Verify autotuned parameters
            run: quarry autotune --verify
            # Warns if hardware mismatch, fails if incompatible
          
          - name: Check performance baseline
            run: quarry perf --check --threshold=5%
            # Fails if any hot function regressed >5%
          
          - name: Re-tune if needed (on schedule)
            if: github.event.schedule  # Weekly scheduled run
            run: |
              quarry autotune
              quarry perf --baseline --update
              # Commit updated Perf.lock if improvements found

This ensures:
  • Autotuned parameters remain optimal (warn on hardware changes)
  • Performance doesn't regress (Perf.lock enforcement)
  • Parameters stay fresh (periodic re-tuning in CI)
  • Both checked into VCS (reproducible, reviewable)

Benefits of Combined Workflow
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Autotuning + Performance Lockfile together provide complete performance governance:

**Autotuning provides:** Machine-optimal parameters for hot functions
**Perf.lock provides:** Regression detection for all functions
**Together:** Optimal performance that stays optimal forever

Example impact:
  • Autotuning: 3.8x speedup from tuned parameters
  • Perf.lock: Catches when future changes break tuning assumptions
  • Result: Performance gains are permanent, not accidental

Without integration:
  - Tune parameters → merge → later commit breaks assumptions → silent regression
  - Parameters chosen for old hardware → deploy on new hardware → suboptimal

With integration:
  - quarry autotune --verify warns: "Tuned for AVX2, deployed with AVX-512 available"
  - quarry perf --check fails: "matrix_multiply regressed 18% (SIMD width dropped)"
  - CI prevents both problems before production

This completes the "reproducible path to maximum performance" that Pyrite 
promises-tuning + verification + enforcement.

Implementation: Stable Release (after algorithmic helpers and profiling are mature)
           Requires: Stable benchmark framework, platform introspection, Perf.lock integration

Performance Cookbook: Stdlib as Learning Resource
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Beyond providing fast implementations, Pyrite's standard library serves as an 
interactive performance education system. Each stdlib algorithm becomes a teaching 
tool that demonstrates "why it's fast" with concrete, measurable examples.

Canonical Implementations with Explanations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Every performance-critical stdlib function includes:

1. **Documented performance characteristics:**
   
       """
       Sorts a slice in-place using pattern-defeating quicksort.
       
       Time complexity: O(n log n) average and worst-case
       Space complexity: O(log n) stack for recursion
       Allocations: 0 (sorts in-place, uses stack recursion)
       
       Performance:
         • 100 elements: ~2 microseconds
         • 10,000 elements: ~400 microseconds  
         • 1,000,000 elements: ~60 milliseconds
       
       Why it's fast:
         • Hybrid algorithm (quicksort + heapsort + insertion sort)
         • Branch prediction friendly (pattern-defeating)
         • Cache-aware partitioning
         • SIMD for small comparisons where applicable
       
       Benchmark: Run 'quarry bench std::sort' to verify on your hardware
       """
       fn sort[T: Ord](slice: &mut [T]):
           ...

2. **Inline performance notes in code:**
   
       fn sort[T: Ord](slice: &mut [T]):
           if slice.len() < 20:
               # Small arrays: insertion sort is fastest
               # Why: No branch mispredictions, excellent cache locality
               insertion_sort(slice)
           else:
               # Large arrays: pattern-defeating quicksort
               # Why: O(n log n) worst-case, cache-friendly partitioning
               pdqsort(slice)

3. **Comparison with alternatives:**
   
       """
       Alternative sorting algorithms in std::
       
       • sort() - General-purpose, fastest for most cases
         Use when: Default choice, no special requirements
         
       • sort_unstable() - May reorder equal elements, ~10% faster
         Use when: Don't care about stability, need maximum speed
         
       • sort_by_key() - Sort by extracted key, avoids comparison overhead
         Use when: Comparing complex types, key extraction is cheap
       
       Choosing the right algorithm:
         Run 'quarry bench --compare sort,sort_unstable,sort_by_key'
         to see performance on your workload
       """

Built-in Benchmark Harness
~~~~~~~~~~~~~~~~~~~~~~~~~~

Every performance-critical stdlib function has associated benchmarks:

    quarry bench std::sort                    # Benchmark sort implementation
    quarry bench std::map::insert             # Benchmark map insertion
    quarry bench std::json::parse             # Benchmark JSON parser
    
    # Compare implementations
    quarry bench --compare std::sort,std::sort_unstable
    
    # Profile specific workload
    quarry bench std::sort --size=10000       # Custom input size

Output shows concrete performance on user's hardware:

    $ quarry bench std::sort
    
    Benchmarking: std::sort
    =======================
    
    Hardware: Intel Core i9-12900K, 48KB L1, 1.25MB L2
    
    Results (sorted Vec<i32>):
      100 elements:      1.8 μs  (55 ns/element)
      1,000 elements:    28 μs   (28 ns/element)
      10,000 elements:   380 μs  (38 ns/element)
      100,000 elements:  5.2 ms  (52 ns/element)
    
    Scaling: O(n log n) confirmed
    
    Memory:
      • Peak allocation: 0 bytes (in-place sort)
      • Stack usage: 892 bytes (recursion depth)
    
    Optimizations observed:
      • SIMD comparisons: AVX2 8-wide for integer types
      • Branch prediction: 94% accuracy (pattern-defeating)
      • Cache misses: 2.3% (excellent locality)
    
    Comparison with std::sort_unstable:
      • sort_unstable: 8% faster (340 μs for 10k elements)
      • Trade-off: May reorder equal elements
      • Use when: Stability not required

This output teaches:
  • What performance to expect (not abstract O(n log n), but "380 μs for 10k ints")
  • Why it's fast (SIMD, branch prediction, cache locality)
  • When to choose alternatives (sort_unstable for 8% speedup)

Canonical Examples with quarry cost Output
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Documentation includes complete examples with cost analysis:

    """
    Example: Efficient JSON parsing
    ================================
    
    This example demonstrates optimal JSON parsing patterns.
    """
    
    fn parse_config_file(path: &str) -> Result[Config, Error]:
        # Read entire file (one syscall, one allocation)
        let contents = try File.read_to_string(path)
        
        # Parse JSON (zero additional allocations with pre-sized arena)
        let json = try json::parse(&contents)
        
        # Extract config (moves data, zero copies)
        return Config::from_json(json)
    
    """
    Cost analysis (quarry cost):
      Allocations: 2 total
        • Line 7: File buffer (~4KB typical)
        • Line 10: JSON parse arena (size based on content)
      
      Copies: 0 (all moves and references)
      
      Syscalls: 1 (file read)
      
      Performance: ~500 μs for typical 4KB config file
      
    Why it's fast:
      • Single allocation for file read (buffered)
      • Zero-copy JSON parsing (references string slices)
      • Move semantics avoid copies
      • Predictable memory usage
    
    Run 'quarry cost example.pyr' to analyze on your code
    """

Interactive Performance Learning
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

quarry learn includes performance-specific exercises:

    $ quarry learn performance
    
    ============================================================
    Performance Exercise: Optimize Hot Loop
    ============================================================
    
    The code below allocates in a loop. Optimize it:
    
    fn process_lines(lines: &[&str]) -> Vec<String>:
        var result = Vec[String].new()
        for line in lines:
            let processed = String.new()  # Allocates every iteration!
            processed.push_str("prefix: ")
            processed.push_str(line)
            result.push(processed)
        return result
    
    Tasks:
      1. Identify the allocation in the loop
      2. Pre-allocate to avoid reallocation
      3. Measure improvement with quarry perf
    
    Target: < 10 allocations for 1000 lines
    
    Hint: Use String::with_capacity() and result.with_capacity()
    [Try] [Hint] [Solution]

Cross-Linked Documentation
~~~~~~~~~~~~~~~~~~~~~~~~~~

Performance patterns reference each other:

    """
    std::algorithm::vectorize
    
    See also:
      • std::simd - Explicit SIMD operations (lower-level)
      • std::algorithm::parallelize - Combine for multi-core + SIMD
      • std::algorithm::tile - Add cache-awareness
      
    Examples:
      • Image processing: docs/examples/image_blur.pyr
      • Matrix operations: docs/examples/matrix_multiply.pyr  
      • Audio processing: docs/examples/fir_filter.pyr
    
    Each example includes:
      • Complete runnable code
      • quarry cost output (static analysis)
      • quarry perf output (runtime profiling)
      • Explanation of optimizations
      • Benchmark comparisons
    """

Cookbook Repository
~~~~~~~~~~~~~~~~~~~

Official performance cookbook (docs/cookbook/) with canonical implementations:

    docs/cookbook/
      ├── algorithms/
      │   ├── matrix_multiply.pyr      # Tiled + SIMD + parallel
      │   ├── fft.pyr                   # Fast Fourier transform
      │   └── sort_variants.pyr         # Comparison of sort algorithms
      ├── data_structures/
      │   ├── cache_friendly_list.pyr   # Memory layout optimization
      │   ├── lock_free_queue.pyr       # Concurrent data structure
      │   └── small_vec_usage.pyr       # Inline storage patterns
      ├── io/
      │   ├── zero_copy_parsing.pyr     # Avoid allocation in parsers
      │   ├── buffered_io.pyr           # Efficient file operations
      │   └── memory_mapped.pyr         # Memory-mapped file I/O
      └── numerical/
          ├── dot_product.pyr           # SIMD inner product
          ├── convolution.pyr           # Cache-aware 2D convolution
          └── tensor_ops.pyr            # Efficient tensor operations

Each cookbook entry:
  • Self-contained, runnable code
  • quarry cost output showing zero or minimal allocations
  • quarry perf benchmarks with expected performance
  • Explanation: "This is fast because..."
  • Alternatives: "Use X if Y condition"
  • Quiz: "Modify this to handle Z case"

Why Performance Cookbook Matters
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This transforms the stdlib from "collection of functions" to "performance 
education system":

1. **Concrete examples beat abstract advice:**
   "See how matrix multiply achieves 15x speedup through tiling" is more valuable 
   than "consider cache locality"

2. **Verifiable performance claims:**
   Every claim ("this is zero-allocation") backed by quarry cost output that 
   readers can reproduce

3. **Benchmark-driven learning:**
   Run the benchmarks, see the numbers, understand why each optimization matters

4. **Canonical patterns:**
   No need to wonder "what's the fast way to parse JSON?" - the cookbook shows the 
   blessed implementation with explanations

5. **Performance becomes accessible:**
   Intermediate developers can copy proven patterns without deep expertise

Impact on Adoption
~~~~~~~~~~~~~~~~~~

The performance cookbook addresses the common complaint: "I know the language is 
fast, but I don't know how to make MY code fast."

With cookbook:
  • "Copy the pattern from docs/cookbook/matrix_multiply.pyr"
  • "Run quarry bench to verify on my hardware"
  • "Understand WHY it's fast from inline comments"
  • "Adapt the pattern to my problem"

This operationalizes "performance is possible" into "performance is the default" 
by providing concrete, proven templates.

Implementation: Stable Release
  • Initial: Core cookbook entries (10-15 canonical examples)
  • Expansion: 50+ examples covering all performance domains
  • Ongoing: Community contributions, benchmarked and reviewed

Cost Transparency Integration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Algorithmic helpers remain transparent, and the two-tier closure model makes 
cost analysis precise:

  • quarry cost shows:
    - "vectorize generates SIMD loop (width=8, closure inlined)"
    - "parallelize spawns 4 threads (parameter closure, zero allocation)"
    - "Thread::spawn allocates closure environment (32 bytes)"
  
  • quarry explain-type on closures distinguishes types:
    - Parameter closure: "Compile-time only, zero bytes, always inlined"
    - Runtime closure: "16 bytes + environment, may allocate, can escape"
  
  • Compiler warnings for inefficient usage:
    - "vectorize width=8 but array length=3 (no benefit)"
    - "parallelize workers=8 but only 100 items (overhead > benefit)"
    - "runtime closure in hot path (consider parameter closure)"

The helpers are ergonomic without being magical. The two-tier closure model makes 
cost explicit: parameter closures (fn[...]) are provably zero-cost, runtime 
closures (fn(...)) show their allocation in quarry cost. This maintains Pyrite's 
transparency principles while enabling powerful abstractions.

Why This Matters
~~~~~~~~~~~~~~~~~

Mojo demonstrated that algorithmic helpers are the "killer feature" for 
performance-oriented languages. They provide:

  • **Approachability:** Scalar logic → SIMD performance
  • **Composability:** vectorize + parallelize = both benefits
  • **Safety:** Compiler enforces correctness (no data races)
  • **Transparency:** Still explicit, inspectable, understandable

Pyrite adopts this proven approach while maintaining its core philosophy: 
explicit is better than implicit, but ergonomic is better than tedious.

## 9.13 GPU Computing (Stable Release)

For GPU-accelerated computing, Pyrite extends its performance contract system 
to heterogeneous computing with a kernel programming model that maintains the 
language's core philosophy: explicit, safe by default, with compiler-verified 
guarantees.

Design Philosophy
~~~~~~~~~~~~~~~~~

Pyrite's GPU support is designed around contracts and blame tracking - the same 
system that makes @noalloc/@cost_budget powerful on CPU extends naturally to 
GPU constraints.

Key principles:
  • Explicit kernel boundaries (no automatic offloading)
  • Contract-based restrictions (@kernel implies @noalloc, @no_panic, etc.)
  • Call-graph blame tracking shows why code can't run on GPU
  • Single-source: write once, target CPU or GPU with same safety guarantees

Kernel Programming Model
~~~~~~~~~~~~~~~~~~~~~~~~

The @kernel attribute marks functions eligible for GPU execution:

    @kernel
    fn saxpy[N: int](a: f32, x: &[f32; N], y: &mut [f32; N]):
        let idx = gpu::thread_id()
        if idx < N:
            y[idx] = a * x[idx] + y[idx]

Kernel contract (automatically enforced):
  • @noalloc - No heap allocation (GPU has no allocator)
  • @no_panic - No panic/abort (GPU can't print or terminate gracefully)
  • @no_recursion - No recursion (limited GPU stack)
  • @no_syscall - No system calls (GPU has no OS)

The compiler enforces these transitively - any function called from a kernel must 
also satisfy kernel contracts.

Call-Graph Blame for GPU
~~~~~~~~~~~~~~~~~~~~~~~~~

When kernel constraints are violated, blame tracking shows exactly why:

    @kernel
    fn process_data(input: &[f32], output: &mut [f32]):
        let result = expensive_compute(input[0])
        output[0] = result
    
    error[P0701]: kernel contract violation: heap allocation
      ----> src/gpu.py:45:18
       |
    43 | @kernel
    44 | fn process_data(input: &[f32], output: &mut [f32]):
    45 |     let result = expensive_compute(input[0])
       |                  ^^^^^^^^^^^^^^^^^^^^^^^^^^^ allocation in kernel
       |
       = note: Call chain:
         1. process_data() [marked @kernel]
            → calls expensive_compute()
         2. expensive_compute() at math.py:234
            → allocates Vec[f64] for intermediate results [VIOLATES @kernel]
       
       = help: To fix this kernel violation:
         1. Rewrite expensive_compute to use fixed-size arrays:
            fn expensive_compute_kernel(input: f32, buffer: &mut [f64; 100]) -> f64
         
         2. Or move allocation to host side:
            let buffer = vec![0.0; 100]  # Host allocation
            gpu::launch(process_data, &input, &mut output, &buffer)
       
       = explain: Run 'pyritec --explain P0701' for kernel programming guide

This makes GPU programming teachable - the compiler explains *why* code can't run 
on GPU and *how* to fix it.

Multi-Backend Support
~~~~~~~~~~~~~~~~~~~~~

Pyrite targets multiple GPU APIs through a unified interface:

    # Compile for specific GPU backend
    quarry build --gpu=cuda      # NVIDIA GPUs (CUDA/PTX)
    quarry build --gpu=hip       # AMD GPUs (HIP/ROCm)
    quarry build --gpu=metal     # Apple GPUs (Metal)
    quarry build --gpu=vulkan    # Cross-vendor (Vulkan compute)

Backend selection is compile-time, not runtime. Single-source code targets 
different GPUs without API-specific code.

Launch API
~~~~~~~~~~

Explicit kernel launch from host code:

    import std::gpu
    
    fn main():
        let n = 1_000_000
        let a = 2.5
        let x = vec![1.0; n]
        let mut y = vec![2.0; n]
        
        # Launch kernel on GPU
        gpu::launch[threads=n, blocks=256](
            saxpy[n],
            a,
            &x,
            &mut y
        )
        
        # Synchronize (wait for GPU completion)
        gpu::sync()
        
        print("Result:", y[0])

Launch parameters:
  • threads: Total work items (like CUDA threads or OpenCL work-items)
  • blocks: Parallelism hint (GPU groups threads into blocks)
  • Compiler generates optimal grid/block configuration per backend

Memory Management
~~~~~~~~~~~~~~~~~

Explicit memory movement between host and device:

    # Allocate on device
    let d_data = gpu::alloc[f32](1000)?
    
    # Copy host → device
    gpu::copy_to_device(&h_data, &d_data)
    
    # Launch kernel
    gpu::launch[threads=1000](process, &d_data)
    
    # Copy device → host
    gpu::copy_to_host(&d_data, &mut h_data)
    
    # Free device memory
    gpu::free(d_data)

Or use RAII wrappers for automatic cleanup:

    let d_data = gpu::DeviceVec::from_host(&h_data)?
    gpu::launch[threads=1000](process, &d_data)
    let result = d_data.to_host()
    # Device memory freed automatically

Integration with Type System
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Device pointers are distinct types:

    type HostPtr[T] = &[T]       # Host memory
    type DevicePtr[T] = gpu::Ptr[T]  # Device memory
    
    @kernel
    fn kernel_func(data: DevicePtr[f32]):
        # Can only access device memory in kernels
    
    fn host_func(data: HostPtr[f32]):
        # Cannot pass host pointer to kernel directly
        # Must explicitly copy to device first

This prevents the common bug of passing host pointers to GPU kernels.

Why This Approach Wins
~~~~~~~~~~~~~~~~~~~~~~

Pyrite's GPU model differentiates through its contract system:

1. **Teachability:** Blame tracking explains GPU restrictions clearly
2. **Safety:** Type system prevents host/device pointer confusion
3. **Composability:** Same contracts work on CPU and GPU
4. **Debuggability:** Know exactly why code can't run on GPU
5. **Simplicity:** One language for CPU and GPU (not separate dialects)

Comparison to other approaches:
  • CUDA/HIP: Separate compilation, easy to mix host/device pointers
  • OpenCL: Verbose, runtime compilation, weak type safety
  • Mojo: Similar goals but less explicit about constraints

Pyrite makes GPU programming accessible while maintaining systems-level control.

Implementation Timeline
~~~~~~~~~~~~~~~~~~~~~~~

  • Stable Release: Design and specify kernel contracts + blame tracking
  • Initial: CUDA backend (NVIDIA GPUs, 80% market share)
  • Expansion: HIP (AMD), Metal (Apple), Vulkan (cross-vendor)

Rationale for late phase: GPU is a powerful differentiator, but requires 
stable CPU-side language first. Get ownership, contracts, and blame tracking 
rock-solid before adding GPU complexity.

This positions Pyrite as: "The systems language that scales from embedded to 
GPU, with the same safety guarantees everywhere."

## 9.14 Why "Batteries Included" Matters
--------------------------------------------------------------------------------

Developer Adoption Barrier
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Languages are often evaluated by: "Can I build X without hunting for 20 
dependencies?" 

Pyrite's comprehensive stdlib means:
  • CLI tool? ✓ (args, file I/O, process)
  • Web scraper? ✓ (HTTP client, regex, JSON)
  • Game? ✓ (math, time, collections)
  • API service? ✓ (HTTP server, JSON, database TBD)

First impressions matter. A newcomer building their first project shouldn't 
spend hours finding, vetting, and integrating dependencies for basic tasks.

Quality and Consistency
~~~~~~~~~~~~~~~~~~~~~~~~

Standard library advantages:
  • Single quality standard
  • Consistent error handling (all use Result)
  • Coherent documentation
  • Security auditing
  • Performance optimization
  • Long-term stability (semantic versioning)

Third-party ecosystem complements stdlib, doesn't replace fundamentals.

Zero-cost Abstractions
~~~~~~~~~~~~~~~~~~~~~~~

The stdlib APIs are designed not to introduce overhead beyond the cost of the 
operations they perform. For example, a sorting function in the library should be 
as efficient as one you would write by hand for a specific type. It will likely 
be generic (sorting any List[T] where T is Comparable), and the compiler will 
optimize it for the concrete type you use. Data structures like List and Map are 
implemented with performance comparable to their C++ or Java counterparts, but 
with safety (no buffer overruns, etc.).

No Hidden Allocations
~~~~~~~~~~~~~~~~~~~~~~

The standard library follows the language's ethos of not hiding costly operations. 
If a function allocates memory or spawns a thread, it's documented and often 
reflected in the API. For instance, pushing an element onto a List that has 
reached capacity will cause a reallocation of the internal array - this is an 
O(n) operation occasionally. The List API would document that append may realloc 
and that you can call reserve(n) to preallocate space if needed to ensure 
amortized constant time appends. By making this explicit, programmers can reason 
about performance. 

In many cases, the library design will require the caller to provide an allocator 
or pick a strategy so that it's never implicit. For example, if you create a 
large String by concatenation, that will allocate new memory; the library might 
provide a StringBuilder to make this efficient and clear. In short, if something 
is potentially expensive, the stdlib will either require you to opt-in (e.g. 
provide an allocator or call a special method) or will be clearly documented to 
avoid surprises.

Memory Safety
~~~~~~~~~~~~~

The standard library is written with the same safe-by-default approach. 
Internally, it might use some unsafe code to achieve performance (for example, 
the internal implementation of List might use pointer arithmetic to move elements 
during reallocation), but this is encapsulated. The public API of List is safe - 
you can't cause a buffer overflow by using it as documented. If a bug is present, 
it's in the stdlib implementation and can be fixed, but your application logic 
remains safe. 

The standard library uses the type system to enforce correctness, e.g., returning 
an Optional when a lookup might fail (instead of a null or an uninitialized 
value). Errors in I/O are returned as Result types, forcing the user to handle 
them.

Error Handling in stdlib
~~~~~~~~~~~~~~~~~~~~~~~~~

As mentioned, functions like opening files will return Result<File, IOError>. 
This encourages robust error handling in user code. If you forget to check an 
error, the compiler will warn that a Result value is unused. This is safer than 
ignoring return codes in C (a very common source of bugs). In Pyrite, it's harder 
to accidentally ignore an error because the type system nudges you.

Global Allocator and Custom Allocators
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Pyrite will likely have a concept of a global default heap allocator (like 
malloc/free under the hood). The stdlib collections by default use this global 
allocator for simplicity. However, for more control, many data structure APIs 
allow passing a custom allocator. For instance, you could create a List with a 
specific allocator (say an arena allocator for many short-lived allocations). 

This pattern is borrowed from Zig, where most functions that allocate take an 
Allocator parameter. Pyrite may not require it on every single call (to keep 
basic usage simple), but it will provide the hooks for when you need them. This 
means you can use Pyrite's stdlib in OS/kernel or embedded contexts by providing 
a no-op or custom allocator, or avoid heap usage entirely if you never call those 
parts (thanks to compile-time, unused code can be eliminated).

Freestanding Support
~~~~~~~~~~~~~~~~~~~~

The standard library is likely split into layers, e.g., a core library that 
doesn't depend on OS (for use in kernels, embedded) and a full library with I/O 
and threads that requires OS support. Rust does this with core vs std. Zig 
similarly has an optional std. Pyrite wants to allow writing code with no stdlib 
if needed (like an OS), or linking only a minimal subset. This is in line with 
providing first-class support for no runtime. If you don't use something, it 
should not be in the binary. For example, a bare-metal program might use 
collections and math from the core library but not use file I/O or threads at 
all.

C Interop in stdlib
~~~~~~~~~~~~~~~~~~~

The stdlib will likely wrap or interface with common C APIs for things like file 
I/O (maybe using OS system calls or C's libc under the hood) and networking 
(sockets). Because Pyrite can call C easily, the implementation can lean on 
proven C libraries where appropriate but present a safer, modern interface.

Concurrency Primitives
~~~~~~~~~~~~~~~~~~~~~~

(Expanding on this important part of the stdlib in its own subsection below.)

## 9.15 Concurrency and Multithreading
--------------------------------------------------------------------------------

Pyrite is built to support concurrent and multi-threaded programming, as these 
are essential for modern software (from servers handling many requests to 
applications with background tasks). The language's memory safety extends to 
concurrency by statically preventing data races. Here's how Pyrite handles 
concurrency:

Threads
~~~~~~~

The stdlib provides a high-level API for threading. For example, there might be a 
Thread.spawn(fn) function or similar that takes a function or closure and runs it 
in a new OS thread. 

E.g.:

    Thread.spawn(fn():
        do_work()
    )

This would spawn a new thread to execute the do_work() function in parallel. 
Under the hood, this uses the OS threading API (like pthread_create on POSIX or 
CreateThread on Windows). The Thread API likely returns a handle or joiner that 
you can use to wait for the thread to finish or detach it.

Closure Capture and 'static Requirement
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you spawn a thread with a closure that captures variables from outside, the 
compiler ensures that either those variables are global or heap-allocated so that 
they outlive the new thread, or it forces you to clone/move them into the thread. 
This prevents scenarios like launching a thread that references a stack variable 
which goes out of scope.

For instance:

    var message = "Hello"
    Thread.spawn(fn():
        print(message)
    )

In this example, message is on the parent thread's stack. Pyrite's compiler would 
forbid capturing it by reference because the new thread could outlive the stack 
frame. It would likely demand that message be moved or be a 'static value. The 
user could do: 

    Thread.spawn(fn(msg=message):
        print(msg)
    )

(Imagining a syntax where we explicitly move message into the closure by value, 
making a copy of the string for the thread.) The compiler might also automatically 
move it if message is owned and not used after, similar to Rust's move closures. 
The key is, the compiler checks and prevents you from accidentally sharing 
something unsafe to share.

Data Race Prevention
~~~~~~~~~~~~~~~~~~~~

Pyrite will likely adopt Rust's concept of Send and Sync traits for types to 
indicate thread-safety. By default, owning a type in one thread and sending it to 
another requires that the type is Send (meaning it has no internal pointer or 
state that could be touched unsafely across threads). Most basic types (ints, 
structs of sendable fields, etc.) are Send. Types like Rc (reference-counted 
pointer without atomic) would not be Send because increasing/decreasing ref count 
from multiple threads would be unsafe. Similarly, having a raw pointer might not 
be Send unless you explicitly mark it. 

These traits (if implemented similar to Rust) are auto-derived by the compiler in 
most cases, or require unsafe impl when appropriate. When you attempt to share 
something between threads (either by moving it to a thread or by using a global 
that multiple threads might access), the compiler will enforce that only 
thread-safe types cross those boundaries.

Shared Mutable State and Synchronization
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In safe Pyrite, you cannot have unsynchronized mutable access to shared data. If 
you want two threads to share an object, you typically would use a 
synchronization primitive from the stdlib:

• Mutex (mutual exclusion lock): e.g., a Mutex[T] that wraps a T and ensures 
  only one thread can access it at a time. The Mutex's API would provide a method 
  to lock and get a &mut T (or some guard object) and automatically unlock on 
  scope exit (RAII style).

• Atomic types: For simple cases like counters or flags, the stdlib will offer 
  atomic integers, atomic booleans, etc., which can be safely shared and updated 
  without a full mutex, using low-level atomic CPU instructions. Pyrite can wrap 
  C11 atomics or use inline assembly for this.

• Channels: A channel is a safe communication queue between threads. For instance, 
  Channel[T] might have a tx (sender) and rx (receiver) handle. One thread can 
  send values of type T into the channel, another can receive them. This is a 
  message-passing concurrency model that avoids sharing data by transferring 
  ownership through the channel. Pyrite's channel could be bounded or unbounded, 
  and internally uses locks or lock-free algorithms. Using a channel, you can 
  design your program to not share mutable memory at all, instead just send 
  messages.

Example of using a channel:

    let (tx, rx) = Channel[int].make()
    Thread.spawn(fn():
        tx.send(42)
    )
    let value = rx.receive()
    print(value)  # prints 42

In this example, one thread sends the integer 42 through the channel, and the 
main thread receives it. The Channel ensures safe handoff of data - 42 is moved 
from one thread to another in this case. Channels in many languages (Rust, Go) 
are a primary tool for concurrency because they sidestep the complexities of 
locking for many scenarios.

All these abstractions (Mutex, Channel, etc.) are built on top of lower-level 
primitives (atomic operations or OS synchronization). They encapsulate the 
unsafety. For example, internally a Mutex might use a raw OS mutex or an atomic 
spinlock, and that involves some unsafe code, but the user of Mutex only deals 
with a safe interface (lock, unlock or RAII guard) that ensures the rules are 
followed.

Because of the ownership and borrowing rules, Pyrite's compiler ensures that if 
two threads access the same memory, it must be through some synchronization 
object. If you try to share a plain &mut T reference or something across threads, 
it just won't compile. The type system plus trait bounds (Send/Sync) and maybe 
some static analysis achieve this guarantee. In Rust, this means safe Rust is 
free of data races. Pyrite aspires to the same: no data races in safe Pyrite 
code. (Data race meaning two threads accessing the same memory concurrently with 
at least one write, without synchronization - which is undefined behavior in 
languages like C/C++.)

No-cost if Not Used
~~~~~~~~~~~~~~~~~~~

If your program does not use threads or any concurrency primitives, none of that 
infrastructure is included in the binary. There is no background thread or 
runtime doing anything implicitly. You only pay for what you use (for example, if 
you never spawn a thread, the Thread code might not even be linked in). This is 
important for embedded or small systems where you might be single-threaded.

Async/Await with Structured Concurrency (Stable Release)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Pyrite will include async/await for high-concurrency applications, but with a 
critical difference from Rust: **structured concurrency by default**.

Traditional async (Rust, JavaScript):

    async fn fetch_data():
        spawn(background_task())  # Fire and forget - task may outlive scope
        let result = await fetch_primary()
        return result
    # background_task may still be running - leak!

Pyrite's structured concurrency:

    async fn fetch_data():
        async with:
            spawn fetch_user()      # Spawned task tracked
            spawn fetch_orders()    # Spawned task tracked
        # BOTH tasks complete before this line
        # No leaked background tasks possible

How it works:

    async with:
        # Scope for structured concurrency
        let user = spawn fetch_user()      # Returns JoinHandle
        let orders = spawn fetch_orders()  # Returns JoinHandle
        # Implicit await for all spawned tasks at scope exit

    # Both complete here - guaranteed

Benefits:
  • **No leaked tasks:** All spawned work completes before scope exit
  • **Prevents common bugs:** Background tasks can't outlive their purpose
  • **Clear reasoning:** Scope shows when work completes
  • **Cancellation propagates:** If parent task cancelled, children cancelled

Comparison with Rust:

    // Rust: Manual tracking required
    async fn process() {
        let handle1 = tokio::spawn(task1());
        let handle2 = tokio::spawn(task2());
        // Easy to forget to await handles
        // Tasks may leak if function returns early
        handle1.await?;
        handle2.await?;
    }
    
    # Pyrite: Automatic tracking
    async fn process():
        async with:
            spawn task1()
            spawn task2()
        # Compiler ensures all complete

Fire-and-forget (opt-in):

If you truly need detached tasks, make it explicit:

    spawn_detached(background_task())  # Explicit: task outlives scope
    # Must use spawn_detached, not spawn

Why structured concurrency matters:

Rust's async is criticized for leaked tasks being a common bug source:
  • Forgot to await a handle → silent task leak
  • Early return → spawned tasks abandoned
  • Error propagation → cleanup tasks not run

Swift and Kotlin already prove structured concurrency works. Pyrite adopts this 
proven pattern.

Integration with error handling:

    async fn process_all() -> Result[(), Error]:
        async with:
            spawn fetch_user()?   # Error propagates, cancels other tasks
            spawn fetch_orders()
        # If any task errors, all others cancelled

Teaching path:
  1. **Beginner:** Use async/await for I/O
  2. **Intermediate:** Learn async with for parallel tasks
  3. **Advanced:** Understand cancellation and propagation
  4. **Expert:** Use spawn_detached when truly needed

This makes Pyrite's async story: "Like Rust's zero-cost async, but without the 
footgun of leaked tasks." Stable Release feature that addresses Rust's main async 
criticism.

In summary, Pyrite's concurrency model is about giving you the tools to do 
multithreading safely: 
  - It prevents you from doing the unsafe things (sharing mutable data 
    willy-nilly). 
  - It provides high-level, easy-to-use abstractions like threads, channels, and 
    mutexes that internally handle the hard parts (locking, etc.) correctly. 
  - It has no garbage collector, but thanks to ownership, memory management in 
    threads is still safe. You can freely send ownership of an object to another 
    thread (if it's Send), and the receiver will free it when done, with no leaks 
    or double frees. 
  - The design mirrors Rust's because Rust has proven that this approach yields 
    fearless concurrency (developers can spawn threads and not worry about memory 
    corruption or data races, as long as they stick to safe code).

## 9.16 Concurrency Primitives (Standard Library)
--------------------------------------------------------------------------------

(Expanding on the concurrency section previously outlined in section 9.2, now 
renumbered appropriately. This remains unchanged from the original spec but 
repositioned for consistency.)

The stdlib provides thread-safe abstractions built on the ownership model:

  • Thread spawning with safe closure capture
  • Mutex[T] for exclusive access
  • RwLock[T] for reader-writer locks
  • Atomic types (AtomicInt, AtomicBool, etc.)
  • Channel[T] for message passing between threads
  • Barrier, Semaphore for synchronization

All concurrency primitives leverage the type system to prevent data races at 
compile time. See section 5 (Memory Management) for details on how Send/Sync 
traits enforce thread safety.

## 9.17 Built-In Observability (Stable Release)
--------------------------------------------------------------------------------

Production systems require visibility into runtime behavior. Pyrite's standard 
library provides first-class observability primitives (logging, tracing, metrics) 
that integrate seamlessly with the language's zero-cost philosophy and can be 
completely eliminated at compile time when not needed.

Design Philosophy
~~~~~~~~~~~~~~~~~

Pyrite's observability follows core principles:
  • **Zero cost when disabled:** Compile-time feature flags eliminate all 
    instrumentation in embedded builds
  • **Structured, not unstructured:** JSON-style structured logging, not printf
  • **OpenTelemetry-compatible:** Industry-standard distributed tracing
  • **Type-safe:** Strongly-typed log fields, metrics, and spans
  • **Composable:** Works with ownership system (no hidden allocations)

Structured Logging
~~~~~~~~~~~~~~~~~~

    import std::log
    
    fn api_handler(req: &Request) -> Result[Response, Error]:
        # Structured logging with typed fields
        log::info("request_received", {
            "method": req.method,
            "path": req.path,
            "user_id": req.user_id,
            "ip": req.remote_addr
        })
        
        let result = try db.query(req)?
        
        log::debug("query_completed", {
            "rows": result.len(),
            "duration_ms": result.duration.as_millis()
        })
        
        return Ok(Response::new(result))

Log Levels
~~~~~~~~~~

    log::trace("...")    # Extremely verbose, disabled by default
    log::debug("...")    # Debug information
    log::info("...")     # Informational
    log::warn("...")     # Warning
    log::error("...")    # Error occurred
    log::fatal("...")    # Fatal error, program will terminate

Configuration:

    # Quarry.toml
    [logging]
    level = "info"                   # Default level
    format = "json"                  # JSON or "pretty" text
    destination = "stderr"           # Where logs go

Distributed Tracing
~~~~~~~~~~~~~~~~~~~

OpenTelemetry-compatible distributed tracing:

    import std::trace
    
    fn process_order(order_id: &str) -> Result[(), Error]:
        # Create trace span
        with span = trace::span("process_order"):
            span.set_attribute("order_id", order_id)
            span.set_attribute("user_id", get_user_id())
            
            # Nested spans
            with db_span = span.child("database_query"):
                let items = try db.fetch_order_items(order_id)?
                db_span.set_attribute("items_count", items.len())
            
            with shipping_span = span.child("calculate_shipping"):
                let cost = try calculate_shipping(&items)?
                shipping_span.set_attribute("shipping_cost", cost)
            
            # Span automatically records duration on scope exit
            return Ok(())

Trace context propagation:

    # Trace context automatically propagates across:
    # - Function calls (via span.current())
    # - Thread boundaries (explicit propagation)
    # - HTTP requests (via headers)
    # - Message queues (via metadata)

Metrics
~~~~~~~

Type-safe metrics collection:

    import std::metrics
    
    fn handle_request(req: &Request) -> Response:
        # Counters
        metrics::counter("http.requests.total").increment()
        metrics::counter("http.requests.by_method")
            .label("method", req.method)
            .increment()
        
        let start = Instant::now()
        
        let response = process_request(req)
        
        # Histograms (distribution of values)
        metrics::histogram("http.request.duration_ms")
            .record(start.elapsed().as_millis())
        
        # Gauges (point-in-time value)
        metrics::gauge("http.active_connections")
            .set(get_active_count())
        
        return response

Metric types:
  • **Counter:** Monotonically increasing (request count, bytes sent)
  • **Gauge:** Point-in-time value (memory usage, queue depth)
  • **Histogram:** Distribution of values (latency, request size)
  • **Summary:** Like histogram with quantiles (p50, p95, p99)

Zero-Cost Elimination
~~~~~~~~~~~~~~~~~~~~~

When observability features are disabled, they're completely eliminated:

    # Embedded build with observability disabled
    $ quarry build --embedded --no-features=observability
    
    # All log, trace, metrics calls compiled to ZERO instructions
    # Binary size: Same as if observability code wasn't there
    # Runtime cost: Absolutely zero

Implementation uses compile-time feature flags:

    # This code:
    log::info("message", {"key": value})
    
    # Compiles to:
    #[cfg(feature = "observability")]
    log::info("message", {"key": value})
    #[cfg(not(feature = "observability"))]
    { /* no-op, optimized away */ }

Cost Transparency
~~~~~~~~~~~~~~~~~

When observability IS enabled, costs are visible:

    $ quarry cost --show-observability
    
    Observability Costs
    ===================
    
    Logging: 47 call sites
      • Allocations: 23 (string formatting)
      • Total cost: ~4 KB per 1000 log calls
    
    Tracing: 12 spans
      • Stack overhead: 48 bytes per span
      • Allocation: Only if spans exported (async)
    
    Metrics: 8 collection sites
      • Lock contention: Atomic operations (no lock)
      • Memory: 16 bytes per metric
      • Update cost: ~5 cycles (atomic increment)

Exporter Configuration
~~~~~~~~~~~~~~~~~~~~~~

Export telemetry to monitoring systems:

    import std::log::exporters
    
    fn main():
        # Configure exporters
        log::set_exporter(exporters::StdErr::new())
        trace::set_exporter(exporters::Jaeger::new("http://localhost:14268"))
        metrics::set_exporter(exporters::Prometheus::new(":9090"))
        
        # Application code
        run_server()

Built-in exporters:
  • Logs: StdOut, StdErr, File, Syslog, JSON
  • Traces: Jaeger, Zipkin, OpenTelemetry Protocol (OTLP)
  • Metrics: Prometheus, StatsD, OpenTelemetry

Custom exporters:

    struct CustomExporter:
        # Implement exporter trait
    
    impl log::Exporter for CustomExporter:
        fn export(&mut self, record: &LogRecord):
            # Send to custom destination

Why Built-In Observability Matters
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Production readiness:**
  • **Cannot achieve widespread adoption without production features**

  • Logs, traces, metrics are non-negotiable for servers
  • Third-party solutions fragment ecosystem
  • Built-in = consistent, compatible, zero-setup

**Competitive landscape:**
  • **Go:** Excellent observability story (built-in + ecosystem)
  • **Rust:** Third-party crates (tracing, log) work well
  • **C/C++:** Manual instrumentation, no standard
  • **Pyrite:** First-class, zero-cost when disabled

**Real-world requirement:**
  • Kubernetes: Logs + metrics expected
  • Observability tools: Prometheus, Grafana, Jaeger standard
  • SRE teams: "How do I debug this in production?"
  • Without observability: "Pyrite is missing production features"

**Embedded vs server trade-off:**
  • Embedded: Observability compiled out (zero cost)
  • Server: Observability essential for debugging
  • Same language, different profiles
  • Feature flags make this seamless

**OpenTelemetry alignment:**
  • Industry standard (CNCF project)
  • Supported by: Datadog, New Relic, Honeycomb, AWS X-Ray
  • Compatible = works with existing infrastructure
  • No vendor lock-in

Use Cases
~~~~~~~~~

  • **Web servers:** Request logging, latency tracking, error rates
  • **Microservices:** Distributed tracing across service boundaries
  • **Batch processing:** Progress tracking, throughput metrics
  • **Embedded (opt-in):** Serial logging, performance counters
  • **Games:** Frame time metrics, event logging

Example Production Usage
~~~~~~~~~~~~~~~~~~~~~~~~

    import std::log
    import std::trace
    import std::metrics
    
    fn main():
        # Initialize observability
        observability::init(Config {
            log_level: Level::Info,
            trace_exporter: Jaeger::new("http://jaeger:14268"),
            metrics_exporter: Prometheus::new(":9090")
        })
        
        # Run application
        with span = trace::span("application_lifetime"):
            run_server()
    
    fn run_server():
        let listener = TcpListener::bind("0.0.0.0:8080")?
        log::info("server_started", {"port": 8080})
        
        for stream in listener.incoming():
            metrics::counter("connections.total").increment()
            
            with span = trace::span("handle_connection"):
                handle_client(stream)

This makes Pyrite credible for production server deployments. Without 
observability, Pyrite is "embedded + CLI tools only." With it, Pyrite is 
"full-stack systems language."

Implementation: Stable Release (after core stdlib is stable)
Priority: High (required for server/cloud adoption)
Complexity: Moderate (exporter integrations, OpenTelemetry compat)
Impact: High (unlocks server/cloud use cases)

---

**Part of**: [Pyrite Language Specification](../SSOT.md)

**Previous**: [Tooling: Quarry Build System](08-tooling.md)

**Next**: [Pyrite Playground and Learning Experience](10-playground.md)
