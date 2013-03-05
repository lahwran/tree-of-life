
root *
    days -

- `days`

-----

    root *
        day: tomorrow -

- `day: tomorrow`
- `*: tomorrow`
- `day: *`
- `tomorrow` (??)
- `*` (or empty)
- `**`

-----

    root
        node1 -
            node2 *
                node3

- `node1 > node2`

-----

    root
        node1 -
            node2 *
                node3

- `node2 < node1`

-----

    root
        node1 *
        ...
        node2 -

- `node1 -> node2`

-----

    root
        node1 -
        ...
        node2 *

- `node2 <- node1`

-----

    root
        node1 *
            node2
                node3 -

- `node1 > > node3`
- `node1 2> node3`
- `node1 >> node3`
- `node1 > * > node3`

-----

    root
        days
            day: today
                task: derp *
                    @active
            day: tomorrow -

- `day: tomorrow`

-----

    root
        task: herp
        days
            day: today
                task: derp *
                    @active
                    task: herp -

- `task: herp`

-----

    root
        task: herp -
        days
            day: today
                task: derp *
                    @active

- `task: herp`


-----

->
<-
<
>


    <search>
    create <search>
    activate <search>


    root
        days
            day: today
                task: whatever
                    @active
                    + task: herpderp
                        + task: herkderk
                            + task: hoopdoop
                task: herpderp
                    + task: herkderk
                        + task: hoopdoop

    task: herpderp > task: herkderk > task: hoopdoop
    Children("task: herpderp",
        Children("task: herkderk",
            Children("task: hoopdoop")))

-----

ORIGIN > day: tomorrow > task: go out to dinner > comment: chinese food
ROOT > ** > day: tomorrow > task: go out to dinner > comment: chinese food


    root
        days
            day: yesterday
                task: go out to dinner
                    + comment: chinese food
            day: today
                task: whatever
                    @active
                    ...
            day: tomorrow
                task: go out to dinner

----- 

root
    days -
        day: today
            task: whatever *


task: whatever < days

-----

day: tomorrow > task: go out to dinner > comment: chinese food
< -> day: tomorrow 

-----

when a node does not exist, it should be put right before the first unfinished task


-----

    root
        task: herp derp
        days
            day: yesterday
                ...
            day: today
                task: something
                    @active
            day: tomorrow
                ...

task: herp derp

this should create a child of task: something, not match
root > task: herp derp


solution: last segment of a create query creates relative to matched parent, period

-----


what happens if

    root
        task: a
            task: b
        days
            day: today
            day: tomorrow
                task: a
                    task: b
                        task: c

and

create task: a > task: b > task: c > task: d

-----

solution:

it creates it as a child of
root > days > day: tomorrow > task: a > task: b > task: c
because only the last one should be created.o


===============================================================================

** for create child, we need three (or more?) positioning markers:

    a
        b (finished)
        c (started)
        d (unstarted)


-----

create a > +e
(at end)
    
    a
        b (finished)
        c (started)
        d (unstarted)
        e


-----

create a > -e
(at beginning)
    
    a
        e
        b (finished)
        c (started)
        d (unstarted)

-----

create a > e
(before next unfinished)

    a
        b (finished)
        c (started)
        e 
        d (unstarted)

-----

create b < e
results in an error

-----

** for create peer, we need to adapt the same three markers to make sense for peers:

    b - *active
    c - finished
    d - started
    e - started
    f - unstarted
    g - unstarted

-----

create b -> new
(before next unfinished)

    b - *active
    c - finished
    new
    d - started
    e - started
    f - unstarted
    g - unstarted

-----


create b -> +new
(at end)

    b - *active
    c - finished
    d - started
    e - started
    f - unstarted
    g - unstarted
    new

-----


create b -> -new
(at beginning)

    b - *active
    new
    c - finished
    d - started
    e - started
    f - unstarted
    g - unstarted


-----

** for create previous peer:

    c - finished
    d - started
    e - started
    f - unstarted
    g - unstarted
    b - *active

-----

create b <- new
(before last unfinished)

    c - finished
    new
    d - started
    e - started
    f - unstarted
    g - unstarted
    b - *active

-----


create b <- +new
(at end)

    c - finished
    d - started
    e - started
    f - unstarted
    g - unstarted
    new
    b - *active

-----


create b <- -new
(at beginning)

    new
    c - finished
    d - started
    e - started
    f - unstarted
    g - unstarted
    b - *active

=============================================================

something to consider: option matching

task: something :{!started}
task: something :{started}
task: something :{started: ??}

maybe have nodes specify what flags they have, so that nodes could say "I match unstarted and unfinished":

task: something :{unstarted}
task: something :{started}
task: something :{unfinished}

task: something :{first}
task: something :{last}

this is going to make index-updating _VERY_ fun ...

* on second thought: first and last should be done via plurality.

for create, + would translate to "after, no tag, plurality last",
default would be "before, tag unfinished, plurality first",
- would translate to "before, no tag, plurality first"

=============================================================

for create we should probably have a way to indicate before/after;
no idea how that would look, maybe a tag...

also, create needs to be tested against empty, because it needs to work
when there is no final point of reference.

create should translate the final segment into a search segment and a create segment:

`+task: derp` should translate to (`* $$last`, `task: derp $$after `)
`-task: derp` should translate to (`* $$first`, `task: derp $$before `)
`task: derp` should translate to (`* $$first $$unfinished`, `task: derp $$before `)
`task: derp $$before $$last` should translate to (`* $$last`, `task: derp $$before`)

============================================================

what syntax should be used to represent tags/plurality?

task: something :{unstarted, first}
task: something $$unstarted $$first
task: something @unstarted @first
task: something @{unstarted, first}

==============================================================

need to have a way to indicate whether to limit or expand plurality. for instance:

    a
        b
        b
        b
    a
        b
        b
    a
        b
    a
        b

create a > b > c

should do:


    a
        b
            c
        b
        b
    a
        b
        b
    a
        b
    a
        b

but there should also be a way to do:


    a
        b
            c
        b
            c
        b
            c
    a
        b
        b
    a
        b
    a
        b

or:

proposed solution is, assuming each search level is based on an iterator:

syntax for segments would become <pattern> <plurality>. possible pluralities
would start out as first, last, many. Syntax for plurality would probably be
the same as syntax for tags - if there is no plurality for a name then it
should be treated as a tag.

=============================================

remaining to do:

create, activate, create-and-activate,
and when they should be default

-> should go to next unfinished peer node
<- should go to prev unfinished peer node
> should go to next unfinished child node
< should go to parent node

-> task: derp
<- task: derp
> task: derp
etc should create and jump if nothing is blocking (ie if nothing is unfinished)

=============================================

need unstart and unfinish commands later

==============================================

pre-index planning

the key things to index will probably be all nodes flattened, and days. Beyond that it is
unlikely to make much difference, as nothing else will be large enough to make a dent in search performance.

the index should be dictionaries of search component to possible matches.

how in the world are we going to maintain ordering? shortcuts cannot be taken for days
as long as other nodes than 'sleep' and 'day' are allowed as children of 'days'.

this should work fine with iterators and such, though.

==============================================

maybe a way to repeat queries for different segments, such as
`segment > (segment1, segment2)`
would expand to two queries, `segment > segment1` and `segment > segment2`


===============================================
===============================================
===============================================
===============================================

final:

node = text_or_star:node (
        ': ' text_or_star:text -> terml.Node(node, text)
        | -> terml.Node(node, None)) |
        '**' -> terml.Flattened()

