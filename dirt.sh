#!/bin/echo "You should *source* this file:"

# ...OR COPY THIS TO YOUR .bashrc AND GO WILD WITH THE ALIASES

export DIRT=
export DIRT_SHARED=/tmp/$USER.dirt

DIRT_SAVED_PROMPT_COMMAND=$PROMPT_COMMAND

touch      $DIRT_SHARED
chmod 0600 $DIRT_SHARED

function dirt_filter()
{
  tr : "\n" | sed "s@^${HOME}@\~@" | sort -u
}

function pcmd()
{
  DIRT=$( echo -e ${DIRT}:${PWD} | dirt_filter | tr "\n" : )
  touch      $DIRT_SHARED.new
  chmod 0600 $DIRT_SHARED.new
  echo ${PWD} | cat $DIRT_SHARED - 2>/dev/null |\
      dirt_filter >> ${DIRT_SHARED}.new &&\
    mv ${DIRT_SHARED}.new ${DIRT_SHARED}
  $DIRT_SAVED_PROMPT_COMMAND
}
PROMPT_COMMAND=pcmd

# Hm. we'll need to borrow a variable. (This is being sourced, remember.)
DIRT=$(cd $(dirname $BASH_ARGV[0]); pwd -L)/dirt.py

alias "s"="  eval \$(python $DIRT    2>&1 1>/dev/tty)"
alias "z"="  eval \$(python $DIRT -z 2>&1 1>/dev/tty)"
alias "b"="  eval \$(python $DIRT -b 2>&1 1>/dev/tty)"
alias "d"="  eval \$(python $DIRT -t 2>&1 1>/dev/tty)"
alias "~~"=" eval \$(python $DIRT -h 2>&1 1>/dev/tty)"
alias "~"="  eval \$(python $DIRT ~  2>&1 1>/dev/tty)"

DIRT=""

# END OF DIRT
