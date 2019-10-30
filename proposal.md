# [RFC] Eventlog tracing system

OCaml currently ships with an instrumented version of the runtime which collects counters and timings for GC events and outputs logs in a custom text format.
Eventlog is a proposed replacement framework, which preserves the existing metrics and adds support for GC trace events in a low-overhead implementation based on a standardized binary trace format ([CTF](https://diamon.org/ctf/)).

Based on an initial design used in OCaml Multicore (inspired by GHC's [ThreadScope](https://wiki.haskell.org/ThreadScope)), this proposal includes an implementation providing:
- The eventlog tracing facility, sitting in the regular OCaml runtime (instead of residing in an alternative runtime to link like the instrumented runtime does.)
- A first trace metadata definition including a set of metrics and counters preserving the feature level of the instrumented runtime.

We provide as well a [script](https://github.com/Engil/gc-tracing/blob/master/scripts/ctf_to_catapult.py) to convert such traces to the
[catapult](https://chromium.googlesource.com/catapult/) event format.
A catapult trace take the form of a `json` file (see the [format description](https://docs.google.com/document/d/1CvAClvFfyA5R-PhYUmn5OOQtYMH4h6I0nSsKchNAySU)),
that can then be read using Google Chrome's own trace viewer, `chrome://tracing`.

### Screenshot from `chrome://tracing`

#### A zoomed-in view on a particular major collection event
<img src="/assets/1.png" width="400px">

#### Duration stats on major collections during the programs lifetime
<img src="/assets/2.png" width="400px">

#### Overview of the trace viewer window on the `zarith` sandmark benchmark
<img src="/assets/3.png" width="400px">

#### Overview of the trace viewer window on the `js_of_ocaml` sandmark benchmark
<img src="/assets/4.png" width="400px">

The statistics gathered, coupled with the available tooling (`chrome://tracing`),
enable core OCaml and application developers to profile the runtime activity: said profile can then be correlated with an application profile to get a full overview of an application's lifetime.
An overview of the garbage collector's timeline also proved very useful to the
Multicore OCaml developers by enabling ways to visualize contention points, relationship between GC phases, and collection event timings.

The implementation is further discussed in the *Implementation* section.

The *Tooling* section provides samples and screenshots of the tooling available with our implementation.

We then discuss the future of our developments on this project in the last section.

## Implementation

Our eventlog port to trunk remains in spirit the same as the one found in OCaml Multicore.
This PR provide our initial implementation of the eventlog framework.

### Overview

The event tracing system adds functions to feed an event buffer that is flushed
to disk once full, and at exit.

In our reference implementation, event tracing functions usually take an `event id`
defined in `caml/eventlog.h` and *counters* where due.
An entry is added into the buffer, and if the buffer is full, a flush is triggered.

Events are flushed in a single CTF *stream*.

The initial target was to collect enough information to be able to match insight
provided by the instrumented runtime.
As such, basic tooling was provided in the spirit of the helpers found
with the source distribution, to be used with the instrumented runtime. (`ocaml-instr-graph` and `ocaml-instr-report`)
Minor/major collections distribution over the
lifetime of the program, metrics on allocations, and timing on the various
phases within GC cycles can be easily visualized with the evailable tooling.

### Format

The main difference will be that instead of emitting traces in the aforementioned
Catapult format, the [Common Trace Format](https://diamon.org/ctf/) is used in our current prototype.

We decided to work with *CTF* for the following reasons:
- Performance: as a binary format, better performances could be easily achieved
  on the serializing front.
- Streaming: the CTF format is comprised of possibly several *streams* holding the event payloads.
  This approach maps well with OCaml Multicore (where each domain could stream its own set of events).
  The notion of stream is also unrelated to the transport mechanism chosen by the implementor.
  As such, it is possible to have a tracer communicate over the network with very low overhead.
  (as a MirageOS program would do, for example.)
- Ecosystem: the CTF ecosystem comes with various visualization tools and a
  C reference implementation bundled with a simple to use Python library.
- Prepare the ground for a streamlined tracing experience within the OCaml ecosystem:
  CTF is a straightforward and generic format. Several users reported using it
  successfully within their own projects.
  We could attempt at providing a unified tracing user experience for the OCaml system.

Our initial implementation aims to stay simple and as such the runtime will output those traces in files.
However we could evolve the tracing infrastructure in the future and provide application-level control over trace distribution or a pub-sub system available from the runtime itself.

#### OCaml CTF metadata

In *CTF*, a *metadata* stream is required in order to allow a CTF codec to parse
the various binary streams composing a trace.
This metadata stream is itself written using CTF's own `TSDL` description format.

An annotated version can be found at this address: [https://github.com/Engil/gc-tracing/blob/master/metadata](https://github.com/Engil/gc-tracing/blob/master/metadata)

Some questions are still open in our implementation:

A complete CTF trace should contain the metadata stream as well.
In its current form (and implementation), its definition is not fully static: the `byte_order`
metadata field depends on which platform the runtime has been executed on.
It has not been decided yet which approach should be taken to distribute the metadata file.
Proposed solutions are to have the runtime generate metadata files, or distribute them as a part of the
compiler installation.

### Control plane

Our implementation provides only simple controls over eventlog's behavior.

Any program built with the OCaml compiler on this branch can be traced by executing the said program with `OCAML_EVENTLOG_ENABLED=1`.

This will output the trace in a `caml-eventlog-pid` file in the running directory. The user can also specify an alternative name for the file using the `OCAML_EVENTLOG_FILENAME` env variable.

Two primitives are exposed by the runtime to pause and resume tracing: `Gc.eventlog_pause` and `Gc.eventlog_resume`.

### Performance measurements

[Sandmark](https://github.com/ocaml-bench/sandmark) was employed to measure the performance impact of eventlog on the runtime. The report can be found [here](https://github.com/Engil/gc-tracing/blob/master/perf_report.pdf).

The associated Jupyter notebook can be found as well for further analysis in this [repository](https://github.com/Engil/gc-tracing). A Docker image can be built for simpler setup.

Early numbers showed a mean slowdown of 1% (comparing an active traced program and the current `trunk`) and a mean slowdown of 0.01% (comparing an non actively traced program with the current `trunk`).

## Tooling

The instrumented runtime ships with two scripts allowing to display and graph various datapoints from the GC's lifetime.

We provide a set of scripts that can be used as a base to run data analysis on our implementation's traces.

`ctf_to_catapult.py` acts as a converter from our trace format to Chrome's eventlog format. Once converted, such traces can then be loaded inside Chrome's `chrome://tracing`.

We provide as well an [example `Jupyter` notebook](https://github.com/Engil/gc-tracing/blob/master/ctf.ipynb)(rendered PDF [here](https://github.com/Engil/gc-tracing/blob/master/ctf.pdf)).
This notebook showcases basic interactions with our implementation's trace format using the babeltrace library.

We made a few example accessible in the [gc-tracing](https://github.com/Engil/gc-tracing/blob/master/sample_traces) repository. `json` files can be loaded into Chrome and are extraced from the related traces found in the various `ctf` subdirectories.

The scripts are prototypes written by reusing the existing ecosystem for CTF traces analysis, mainly using the reference implementation for CTF, `babeltrace`.
An OCaml binding to the `babeltrace` library is planned and would enable trace processing and analysis from OCaml programs.

## Eventlog future timeline

### Deprecating the instrumented runtime

We aim to merge the tracing runtime with a feature level at least matching the instrumented runtime's.
We believe the tracing runtime can have a sufficiently low overhead so that it
can sit in the regular runtime without overly impacting performances in programs
that do not use the feature.

Removing it would as well speed up OCaml's compilation, by not having to build an extra runtime.
A more straightforward approach to statistics gathering sitting in the main runtime would also simplify maintenance:
While working on porting the `eventlog` framework to trunk we found a long standing
inconsistency within the instrumented runtime's output. (see GPR #9004)

The inclusion of the eventlog framework adds as well a bit of duplicate noise in the codebase, as it trace similar codepaths as the instrumented runtime.

As such we will submit a second PR to deprecate the instrumented runtime from the OCaml distribution.

### Future: user-based events, user-controlled streaming mechanisms

We plan to extend the eventlog framework further by adding support for user defined events and extra mechanism for traces extraction.

User defined events would allow developers to implement their own set of events from the application level. Such events could then be easily correlated with the runtime's own set of events.

We also had discussions about opening new extraction channels for eventlog's streams. This would prove useful for production systems or Mirage application (extracting traces via network or a serial port... etc).

The timeline for these features is undefined as discussions about their respective designs are still ongoing.
