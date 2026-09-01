// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract FreelanceEscrow {

    enum JobStatus {
        Open,
        Assigned,
        Submitted,
        Approved,
        Released,
        Refunded
    }

    struct Job {
        uint256 jobId;
        address payable client;
        address payable freelancer;
        uint256 amount;
        string jobTitle;
        string ipfsCID;
        uint256 aiScore;
        JobStatus status;
    }

    mapping(uint256 => Job) public jobs;
    
    event JobCreated(
    uint256 indexed jobId,
    address indexed client,
    uint256 amount
);

event FreelancerAssigned(
    uint256 indexed jobId,
    address indexed freelancer
);

event WorkSubmitted(
    uint256 indexed jobId,
    string ipfsCID,
    uint256 aiScore
);

event PaymentReleased(
    uint256 indexed jobId,
    address indexed freelancer,
    uint256 amount
);

event RefundIssued(
    uint256 indexed jobId,
    address indexed client,
    uint256 amount
);

modifier jobExists(uint256 _jobId) {
    require(jobs[_jobId].client != address(0), "Job does not exist");
    _;
}

function createJob(
    uint256 _jobId,
    string memory _jobTitle
) public payable {

    require(msg.value > 0, "Payment required");

    require(
        jobs[_jobId].client == address(0),
        "Job already exists"
    );

    jobs[_jobId] = Job({
        jobId: _jobId,
        client: payable(msg.sender),
        freelancer: payable(address(0)),
        amount: msg.value,
        jobTitle: _jobTitle,
        ipfsCID: "",
        aiScore: 0,
        status: JobStatus.Open
    });

    emit JobCreated(
        _jobId,
        msg.sender,
        msg.value
    );
}
function assignFreelancer(
    uint256 _jobId,
    address payable _freelancer
)
    public
    jobExists(_jobId)
{
    Job storage job = jobs[_jobId];

    require(
        msg.sender == job.client,
        "Only client can assign freelancer"
    );

    require(
        job.status == JobStatus.Open,
        "Job is not open"
    );

    job.freelancer = _freelancer;
    job.status = JobStatus.Assigned;

    emit FreelancerAssigned(
        _jobId,
        _freelancer
    );
}
function submitWork(
    uint256 _jobId,
    string memory _ipfsCID,
    string memory _submissionType
) public jobExists(_jobId) {
    Job storage job = jobs[_jobId];

    require(msg.sender == job.freelancer, "Only assigned freelancer can submit");
    require(job.status == JobStatus.Assigned, "Job not assigned");

    require(
        keccak256(bytes(_submissionType)) == keccak256(bytes("text")) ||
        keccak256(bytes(_submissionType)) == keccak256(bytes("code")) ||
        keccak256(bytes(_submissionType)) == keccak256(bytes("image")) ||
        keccak256(bytes(_submissionType)) == keccak256(bytes("audio")),
        "Invalid submission type"
    );

    job.ipfsCID = _ipfsCID;
    job.submissionType = _submissionType;
    job.status = JobStatus.Submitted;

    emit WorkSubmitted(_jobId, _ipfsCID);
}

function releasePayment(
    uint256 _jobId
)
    public
    jobExists(_jobId)
{
    Job storage job = jobs[_jobId];

    require(
        msg.sender == job.client,
        "Only client can release payment"
    );

    require(
        job.status == JobStatus.Submitted,
        "Work not submitted"
    );

    require(
        job.aiScore >= 70,
        "AI score below threshold"
    );

    job.status = JobStatus.Released;

    (bool success, ) = job.freelancer.call{value: job.amount}("");
require(success, "Payment transfer failed");

    emit PaymentReleased(
        _jobId,
        job.freelancer,
        job.amount
    );
}

function refundClient(
    uint256 _jobId
)
    public
    jobExists(_jobId)
{
    Job storage job = jobs[_jobId];

    require(
        msg.sender == job.client,
        "Only client can refund"
    );

    require(
        job.status != JobStatus.Released,
        "Payment already released"
    );

    job.status = JobStatus.Refunded;

    (bool success, ) = job.client.call{value: job.amount}("");
require(success, "Refund transfer failed");
    emit RefundIssued(
        _jobId,
        job.client,
        job.amount
    );
}
function getJob(
    uint256 _jobId
)
    public
    view
    returns (Job memory)
{
    return jobs[_jobId];
}
}