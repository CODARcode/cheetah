campaign=gs
sweepgroup=gsc
exe=cheetah.py

c=compression

create: 
	${exe} create-campaign -a . -o ${campaign} -e ${campaign}.py -m local
run:
	${campaign}/${USER}/run-all.sh
cancel:
	${campaign}/${USER}/${sweepgroup}/cancel.sh
status:
	${exe} status ${campaign} -s
report:
	${exe} status ${campaign} -t -p
check0:
	cat ${campaign}/${USER}/${sweepgroup}/run-0.iteration-0/${c}/codar.workflow.stdout.${c}

clean:
	rm -rf *~ ${campaign} __pycache__ 
