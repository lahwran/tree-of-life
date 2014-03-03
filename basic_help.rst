error
    dumps a test error to make sure the system is working
restart
    restarts the back end
stop
    stops the back end
save
    commits the full current life tree to git. very hard to break.
update
    refreshes the ui in case it's out of date. only useful for working around bugs
edit
    opens the tree in your editor of choice. more detail required.
editpudb
    initializes pudb and then does edit
done
    attempts to finish the currently active task. if there are any unfinished child nodes of the current task, then it activates the first of those instead of finishing. otherwise, it looks for tasks after the active one and tries to activate one of those. If none of those can be activated, activates the parent.
createauto
    the default if you don't specify any other command. if the first word (up until the first space) is not a valid command, then the whole command line you send will be prefixed with createauto. eg, "task: test" becomes "createauto task: test". because of this, this will be your most used command. it takes a search as an argument. it will first attempt to find any results of that search, and activate the first one. if that search has no results, it will attempt to execute it as a "create" search. 
create, or "c"
    can also be written as just c. takes a "create" search and executes it. does not attempt to search for existing nodes and does not activate the created node. 
activate, or "a"
    can also be written as just a. takes a search and activates the first found node. does not create.
forceactivate, or "fa"
    takes a search and activates the first found node, even if it's already been finished. does not create. 
finish, or "f"
    takes a search, activates the first found node, and finishes the previously active node. 
createactivate, or "ca"
    takes a create search, creates the node, and then activates it
createfinish, or "cf"
    takes a create search, creates the node, activates it, and finishes the previously active node. 

searching
    a search is a series of filters, each of the form "nodetype: text". if you leave off the nodetype, it will check to see if the text is a valid nodetype, and if so, treat it as a filter for nodetype and you don't care about text.     
    if you wrote "comment", on its own, then it's a filter for all nodes that are comments
    writing "comment" is like writing "comment: *"
    if you write "*", it matches any node
    if you write "*: *", that's the same as writing "*"
    if you write "*: hello", it matches all nodes that have the text "hello" without paying any attention to their node types
    if you write "hello: *", it matches any node that is node type hello, without paying any attention to node text
    if you just write "hello" on its own, though, then it will check to see if there is a node type called "hello", and if so, it will be the same as "hello: *"
    if there is not a node type called "hello" it will treat it as the same as "*: hello"

    a search is a series of segments. a segment is a relationship and a pattern
    the relationship is the relation to the results of the previous segment, or the first node
    the relationship can be one of ">", which means "previous match's children"; "<", which means "previous match's parents"; "->", which means "previous match's peers, following"; "<-", which means "previous match's peers, preceding"
    there are also two others, "**" and "<<", which I almost never use. "**" is "previous match's children, and their children, and so on, flattened"
    "<<" is "root node"
    so some examples of searches might be:
        comment: something
        comment
        days > day: today
        task > task > target
        days > day > depends
        -> task: target: with colon
    each of these will search relative to a starting node
    so say that, as a child of the active task, I have "comment: something" as a node
    the search "comment: something" will find it. as will "comment". or "something".
    if I search from the root node, then "days > day: today" will find today.
    if I search from the currently active node, and I have a bunch of nested tasks and one of them is named target, then "task > task > target" will find 1. all children that are tasks, 2. all of those tasks's children that are also tasks, and 3. all of those children's children that are labeled "target"
    if the first node text can be used as a node ID, it will be. so the search "#00000 > comment: something" will find children of the root node, and only find those children that match "comment: something".
    (the root node always has id "00000".)
    if the first node text in the search can be used as a day, and you don't specify a node type, it will be used as a day. (this is a recent feature as of last week)
    so, if you search from anywhere, and search for "today", it will ALWAYS find today. always.
    if you search from anywhere for "tomorrow", it will find tomorrow.
    (if you search for "today > tomorrow", that will have no results, because tomorrow is not a child of today.)
    if you search for _anything that the system knows how to parse as a date_ as the first text then it will try to treat it as a day before treating it normally (which it will also do).
    so if you search for "april 22 2016 > comment: will have car paid off" then it will find it.
    if you instead search for any of "apr 22, 2016", "APrIL 22,            2016", then that will STILL WORK.
    it is very flexible on the date parsey business.

    now, for the other major part of searches.
    now, keep in mind, I want to be changing this soon. it's kinda odd, and can be improved.
    but, right now, create searches
    a create search is mostly just like a normal search. it still has segments, and etc. but, the last item in a create search will be created, rather than searched for.
    so if you do a createsearch for "april 12, 2014" then it will try to *create* that day.
    for everything besides days, you need to prefix the last item with a node type in order to do a create search. if you don't prefix it with a node type it will complain loudly (well, quietly but in red letters).
    you cannot create multiple nodes at once with create searches. (that's a big part of why I want to change them.)
    so, for instance, trying to run a createsearch for "around the world" will be an error, because it doesn't know what node type to use.
    it'll say "cannot create without full node".
    so, if you already have a day node for april 12th, 2014; then you can do a createsearch for "apr 12, 2014 > comment: BEST TALKS IN ALL OF PYCON!!"
    and it will create that comment node.
    note: I currently have a couple of related bugs where 1. you can create duplicates of days. so if you try to create a day node that already exists, it will WORK, and you'll end up with TWO. keep in mind that I have been aware of that for a while and it won't break anything or lose data, it's just annoying and requires opening the editor to fix.
    and 2. you can activate tasks that are in far-distant days. I discovered that by accident.
    you can have as many segments as you want on the same createsearch or normal-search
    though I rarely have more than two
    there are places in the code where I have many
    you don't need to have more than one segment to use a createsearch
    if you do a createsearch for just "task: work", for instance, then that will simply create a task "work".
    oh, oops, I forgot to mention that. the first segment will default to ">", the children relationship, if you don't specify one.
    the first segment's relationship is relative to the start node (unless overridden by an #id or a date). when using the UI, the start node will almost always be the active node (in fact, right now that's the only thing that's possible).
    so, say the currently active task is today's day node. someone tells me that next saturday there's an event. unfortunately, right now, you have to figure out the date for next saturday still
    but once you do, you say something like this:
    c jan 11, 1887
    c jan 11, 1887 > comment: big event! best witchhunt this whole winter!
    and that creates it.
    then later, it's getting closer, and you find out more information about the event, so you want to add it to the same day
    you simply do
    c jan 11, 1887 > comment: crap, they think I'm a witch
    then a few weeks later you have another note
    c jan 11, 1887 > comment: that wasn't as bad as I thought, turns out I am a witch and my powers saved me
    it's now february 22, 1887, and you need to go milk the cows today (can you tell how little I know about life before about 1950?). you just got up, and you're thinking about it, so you'll make the note now
    so you do:
    c task: milk the cows
    there are a couple more things I haven't mentioned about searches. one is stupid and I'm going to remove it (it's ":{}" in case you ever see it), and the other is create positions
    when creating a node, you can put + and - before it to say "as close as you can" and "as far as you can"
    so, say you have a bunch of tasks for today. today is currently the active node, because you haven't started any of them. so you do "c task: something".
    unfortunately, task: something was put at the *beginning* of the day, because you haven't started any of the tasks yet.
    you wanted it at the end
    so you tell it to put it as far as it can go:
    c +task: something
    and that puts it at the end of the day.
    alternately, you've done half the day's tasks. you're taking an unplanned, unstructured break, so you simply do:
    fa <
    and it activates the day node again.
    er, I LIED. damn, usability bug. that's "force activate".
    I thought it was "finish and activate". whooops.
    anyway, you do something like "a <", or "a today", or in some other way jump to the day node for today.
    then you want to create another task. half of the tasks for today are finished. so if you do "c task: another thing", it will go right before the first task that you haven't finished
    but you want it to be before everything (not sure why, but you do). so you say "c -task: another thing", and it goes at the very beginning, before any of the finished tasks.
    there. that's almost all the functionality I have.
    some commands I've done recently:
    c mar 3 2014
    c mar 3 2014 > comment: ml class starts
    f -> task: hang out, treeoflife
    that had an error because I hadn't made the node yet, so I followed it with
    cf -> task: hang out, treeoflife
    c march 22, 2014
    c march 22, 2014 > event: go to appointment
    c mar 8 2014
    c mar 8 2014 > task: meetup, need to give a ride
    c mar 8 2014 > task > comment: 3pmish
    you'll notice lots of redundancy there :) I have various ideas on what to do about all that. ideally most of those would have been one command.
    for instance it would have been nice to do, say, "c mar 8 2014 > task: meetup @time: 3pm @prep: ~half an hour
    and have it understand all that
