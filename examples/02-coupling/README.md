# Using Cheetah to run coupled applications

This is a simple producer-consumer workflow where the producer generates a 1D array of integers, which is read by the consumer to calculate the mean of the local array.

The coupling is done via ADIOS SST, and the data is published as an ADIOS bp file.

`cheetah-campaign.py` shows how to create a campaign to run the simulation using different sizes of the local array.

Create the campaign on a local machine as  
`cheetah create-campaign -a ./ -e cheetah-campaign.py -m local -o ./ex-02-campaign`.

Then navigate to the campaign and run it as:
```
cd ./ex-02-campaign/${whoami}  
./run-all.sh
```

When the campaign is being run, you can inspect Cheetah's log file for a Sweep Group as:
```
cd ./ex-02-campaign/${whoami}/sg-1  
less codar.FOBrun.log
```

The status of the experiments can be queried as:  
`cheetah status ./ex-02-campaign -n`

