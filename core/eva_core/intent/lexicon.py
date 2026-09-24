# A centralized lexicon for intent matching
INTENT_LEXICON = {
    "conversation": {
        "exact": [
            "hello", "hi", "hii", "hiii", "hey", "heyy", "hlo", "helo", "helloo",
            "hello eva", "hi eva", "hii eva", "hey eva", "helo eva",
            "good morning", "good afternoon", "good evening",
            "how are you", "how are you doing", "whats up", "what is up"
        ]
    },
    "application_operation": {
        "prefixes": [
            "open", "launch", "start", "run",
            "please open", "can you open", "could you launch", "start"
        ],
        "apps": [
            "chrome", "google chrome",
            "firefox",
            "vscode", "vs code", "visual studio code", "code",
            "terminal",
            "notepad",
            "calculator",
            "file manager"
        ]
    },
    "file_operation": {
        "exact": [
            "create file", "make file", "new file", "create a file",
            "create folder", "make folder", "new folder", "create directory", "make directory", "create a folder",
            "list files", "show files", "show my files", "list directory",
            "read file", "open file", "view file contents",
            "rename file", "move file", "copy file"
        ]
    },
    "browser_operation": {
        "exact": [
            "search for ai agents",
            "search the web for ai agents",
            "search online for ai agents",
            "google ai agents",
            "look up ai agents",
            "find information about ai agents online",
            "browse for ai agents",
            "please search for ai agents",
            "can you search the web for ai agents",
            "search ai agents on google"
        ],
        "prefixes": [
            "search for", "search the web for", "search online for", "google", "look up", "find information about", "browse for"
        ]
    },
    "document_operation": {
        "exact": [
            "create document", "create a document", "make a document",
            "create word document", "make a word file", "create word report",
            "open document", "edit document", "modify document", "save document",
            "write report", "create presentation", "create spreadsheet", "create a word document"
        ]
    },
    "system_command": {
        "exact": [
            "ss", "screenshot", "take a screenshot", "take screenshot",
            "shutdown computer", "restart computer", "lock computer",
            "check system status", "check cpu usage", "check memory usage",
            "show disk usage", "turn off wifi", "enable wifi"
        ]
    }
}
