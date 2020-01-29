[Main](../index)

Creating a Campaign Endpoint from a Spec File
=============================================

Once a specification has been created, create a campaign end-point, which is a directory hierarchy consisting of SweepGroups as batch jobs, and Sweeps serialized into experiments with their independent workspaces.

`cheetah create -a path-to-app-binaries -e spec-file -m machine-name -o path-to-campaign-endpoint`

In the campaign endpoint, a sub-directory for the user is created. Multiple users can run experiments under the same campaign endpoint.


Next, see how to [run a campaign](campaign-run).

[Main](../index)

