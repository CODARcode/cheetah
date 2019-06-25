campaign="gs"
sweepgroup="gsc"
exe="compression"

create: 
	cheetah.py create-campaign -a . -o ${campaign} -e ${campaign}.py -m local
run:
	${campaign}/${USER}/run-all.sh
cancel:
	${campaign}/${USER}/${sweepgroup}/cancel.sh
status:
	cheetah.py status ${campaign} -s
report:
	cheetah.py status ${campaign} -t -p
check0:
	cat ${campaign}/${USER}/${sweepgroup}/run-0.iteration-0/${exe}/codar.workflow.stdout.${exe}

clean:
	rm -rf *~ ${campaign} __pycache__ 
