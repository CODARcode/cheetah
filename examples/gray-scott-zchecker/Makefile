campaign="gs"

create: 
	cheetah.py create-campaign -a . -o ${campaign} -e ${campaign}.py -m local
run:
	${campaign}/${USER}/run-all.sh
cancel:
	${campaign}/${USER}/Gray-Scott-A/cancel.sh
status:
	cheetah.py status ${campaign} -s
report:
	cheetah.py status ${campaign} -t -p
clean:
	rm -rf *~ ${campaign} __pycache__ 
