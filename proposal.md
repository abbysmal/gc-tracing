# Event Tracing System proposal

Multicore OCaml includes an event tracing system that act as a GC
profiling tool for the development effort on the multicore runtime.

Inspired by GHC's [ThreadScope](https://wiki.haskell.org/ThreadScope), the idea
is provide a low-overhead framework to collect runtime events and statistics,
and process them offline in order to profile and debug performance problems.

Multicore OCaml emit such event traces in a format compatible with the
[catapult](https://chromium.googlesource.com/catapult/) toolchain.
A catapult trace take the form of a `json` file (see the [format description](https://docs.google.com/document/d/1CvAClvFfyA5R-PhYUmn5OOQtYMH4h6I0nSsKchNAySU)),
that can then be read using Google Chrome's own trace viewer, `chrome://tracing`.

Our proposal is to introduce the event tracing system in OCaml,
and have it replace the existing instrumented runtime.

## Deprecating the instrumented runtime

As we aim to merge the tracing runtime with a feature level at least matching
the instrumented runtime's, we will deprecate it with a joint pull request.
We believe the tracing runtime can have a sufficiently low overhead so that it
can sit in the regular runtime without overly impacting performances in programs
not making use of the feature.

Removing it would as well speed up OCaml's compilation, by not having to build an extra runtime.
A more straightforward approach to statistics gathering sitting in the main runtime would also simplify maintenance:
While working on porting the `eventlog` framework to trunk we found a long standing
inconsistency within the instrumented runtime's output. (see GPR #9004)

We will provide a PR to deprecate the instrumented runtime from the OCaml distribution to go alongside this work at a later date.

## Event Tracing System Implementation

The tracing system port will remain in spirit the same as the one found in OCaml Multicore.

### Traces format

The main difference will be that instead of emitting traces in the aforementioned
Catapult format, the [Common Trace Format](https://diamon.org/ctf/) is used in our current prototype.

We decided to work with *CTF* for the following reasons:
- Performance: as a binary format, better performances could be easily achieved
  on the serializing front.
- Streaming: the CTF format is comprised of possibly several *stream* holding the event payloads.
  This approach maps well with OCaml Multicore (where each domain could stream its own set of events).
  The notion of stream is also unrelated to the transport mechanism chosen by the implementor.
  As such, it is possible the have a tracer communicate over the network with very low overhead.
  (as a MirageOS program would do, for example.)
- Ecosystem: the CTF ecosystem comes with various visualization tools and a
  C reference implementation bundled with a simple to use Python library.
- Build the foundation to a tracing experience within the OCaml ecosystem:
  CTF is a straightforaward and generic format. Several users reported using it
  successfully within their own projects.
  We could attempt at providing a unified tracing user experience for the OCaml system.

Our initial implementation aims to stay simple and as such the runtime will output those traces in files.
However we could evolve the tracing infrastructure in the future and provide application-level control over trace distribution or a pub-sub system available from the runtime itself.

### Overview of the implementation

The event tracing system adds functions to feed an event buffer that is flushed
to disk once full, and at exit.

In our reference implementation, event tracing functions usually take an `event id`
defined in `caml/eventlog.h` and *counters* where due.
An entry is added into the buffer, and if the buffer is full, a flush is triggered.

Events are flushed in a single CTF *stream*.

The initial target is to collect enough information to be able to match insight
provided by the instrumented runtime.
As such, basic tooling will be provided in the spirit of the helpers provided
with the source distribution for the instrumented runtime.
Showing minor/major collections distribution over the
lifetime of the program, metrics on allocations, and timing on the various
phases within GC cycles.

The traces can be extended further in the future by versioning the format,
so the tooling around it can evolve gracefully.

## OCaml CTF metadata

In *CTF*, a *metadata* stream is required in order to allow a CTF codec to parse
the various binary streams composing a trace.
This metadata stream is itself written using CTF's own `TSDL` description format.

An annotated version can be found at this address: [https://github.com/Engil/gc-tracing/blob/master/metadata](https://github.com/Engil/gc-tracing/blob/master/metadata)

Some questions are still open in our implementation:

A complete CTF trace should contain the metadata stream as well.
In its current form (and implementation), its definition is not fully static: the `byte_order`
metadata field must be provided depending on which platform the runtime has been executed on.
It has not been decided yet which approach should be taken to distribute the metadata file.
Proposed solutions are to have the runtime generate metadata files, or distribute them as a part of the
compiler installation.

## Performance measurements

[Sandmark](https://github.com/ocaml-bench/sandmark) was employed to measure performance impact of our implementation.

The report can be found [here](https://github.com/Engil/gc-tracing/blob/master/perf_report.pdf).

The associated Jupyter notebook can be found as well for further analysis in this [repository](https://github.com/Engil/gc-tracing). A Docker image can be built for simpler setup.

### Tooling

The instrumented runtime ships with two scripts allowing to display and graph various datapoints from the GC's lifetime.

We provide a set of scripts that can be used as a base to run data analysis on our implementation's traces.

`ctf_to_catapult.py` acts as a converter from our trace format to Chrome's eventlog format. Once converted, such traces can then be loaded inside Chrome's `chrome://tracing`.

We provide as well an [example `Jupyter` notebook](https://github.com/Engil/gc-tracing/blob/master/ctf.ipynb)(rendered PDF [here](https://github.com/Engil/gc-tracing/blob/master/ctf.pdf)).

We made a few example accessible in the [gc-tracing](https://github.com/Engil/gc-tracing/sample_traces) repository. `json` files can be loaded into Chrome and are extraced from the related traces found in the various `ctf` subdirectories.
