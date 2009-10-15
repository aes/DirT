#!/bin/echo "You should *source* this file:"

# COPY THIS TO YOUR .bashrc AND GO WILD WITH THE ALIASES

export DIRT=

DIRT_SAVED_PROMPT_COMMAND=$PROMPT_COMMAND

function pcmd()
{
  DIRT=$( echo -e ${DIRT}:${PWD} |\
          tr : "\n" |\
          sed "s@^${HOME}@\~@" |\
          sort -u |\
          tr "\n" : )
  $DIRT_SAVED_PROMPT_COMMAND
}
PROMPT_COMMAND=pcmd

# Hm. we'll need to borrow a variable. (This is being sourced, remember.)
DIRT=$(cd $(dirname $BASH_ARGV[0]); pwd -L)/dirt.py

alias "s"="eval \$(python $DIRT    2>&1 1>/dev/tty)"
alias "b"="eval \$(python $DIRT -b 2>&1 1>/dev/tty)"
alias "d"="eval \$(python $DIRT -t 2>&1 1>/dev/tty)"
alias "~~"="eval \$(python $DIRT -h 2>&1 1>/dev/tty)"
alias "~"="eval \$(python $DIRT ~  2>&1 1>/dev/tty)"

DIRT=""

# END OF DIRT
