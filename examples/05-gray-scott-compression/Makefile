campaign=gs
sweepgroup=gsc
exe=/home/igor/test1/cheetah/bin/cheetah

c=compress

run: create
	${campaign}/${USER}/run-all.sh
create: 
	${exe} create-campaign -a . -o ${campaign} -e ${campaign}.py -m local
cancel:
	${campaign}/${USER}/${sweepgroup}/cancel.sh
status:
	${exe} status ${campaign} -s
report:
	${exe} status ${campaign} -t -p
check0:
	cat ${campaign}/${USER}/${sweepgroup}/run-0.iteration-0/${c}/codar.workflow.stdout.${c}
check1:
	cat ${campaign}/${USER}/${sweepgroup}/run-1.iteration-0/${c}/codar.workflow.stdout.${c}
check2:
	cat ${campaign}/${USER}/${sweepgroup}/run-2.iteration-0/${c}/codar.workflow.stdout.${c}
check3:
	cat ${campaign}/${USER}/${sweepgroup}/run-3.iteration-0/${c}/codar.workflow.stdout.${c}

clean:
	rm -rf *~ ${campaign} __pycache__ 
