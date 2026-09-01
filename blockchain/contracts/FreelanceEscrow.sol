// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/**
 * INTERFACE FOR ReputationNFT
 * ============================
 * This lets FreelanceEscrow call ReputationNFT's mintReputation() function
 * WITHOUT needing to import the whole contract -- it just needs to know
 * this one function exists and what it expects. Think of this as a
 * "menu" telling FreelanceEscrow what it's allowed to order from the
 * ReputationNFT contract.
 */
interface IReputationNFT {
    function mintReputation(address freelancer, uint256 aiScore) external;
}

/**
 * FreelanceEscrow (Fixed Version)
 * ================================
 *
 * THREE FIXES APPLIED FROM THE ORIGINAL VERSION:
 *
 * FIX 1 -- Score Oracle (was: freelancer self-reported their own score)
 *   Only one trusted address (the "oracle" -- your Python/web3.py
 *   script's wallet) is allowed to report the AI compliance score.
 *   The freelancer can no longer just claim any score they want.
 *
 * FIX 2 -- Automatic release (was: client had to manually approve)
 *   The moment the oracle reports a score that clears the threshold,
 *   payment releases immediately in that SAME transaction -- no
 *   separate manual approval step from the client is needed anymore.
 *   This is what actually makes the system "AI-gated" rather than
 *   "AI-suggested, human-approved."
 *
 * FIX 3 -- Direct reputation link (was: two disconnected contracts)
 *   When payment releases successfully, this contract directly calls
 *   ReputationNFT.mintReputation() in the same transaction, so the
 *   freelancer's reputation update happens automatically, not as a
 *   separate manual step someone has to remember to do.
 */
contract FreelanceEscrow {

    enum JobStatus {
        Open,
        Assigned,
        Submitted,
        Released,
        Held,
        Refunded
    }

    struct Job {
    uint256 jobId;
    address payable client;
    address payable freelancer;
    uint256 amount;
    uint256 threshold;
    string jobTitle;
    string ipfsCID;
    string submissionType;
    uint256 aiScore;
    JobStatus status;
}

    mapping(uint256 => Job) public jobs;

    // FIX 1: only this address can report AI scores -- set once at
    // deployment to your Python/web3.py bridge's wallet address.
    address public scoreOracle;

    // FIX 3: the deployed ReputationNFT contract this escrow talks to.
    IReputationNFT public reputationContract;

    event JobCreated(uint256 indexed jobId, address indexed client, uint256 amount, uint256 threshold);
    event FreelancerAssigned(uint256 indexed jobId, address indexed freelancer);
    event WorkSubmitted(
    uint256 indexed jobId,
    string ipfsCID,
    string submissionType);
    event ScoreRecorded(uint256 indexed jobId, uint256 aiScore);
    event PaymentReleased(uint256 indexed jobId, address indexed freelancer, uint256 amount);
    event PaymentHeld(uint256 indexed jobId, uint256 aiScore, uint256 threshold);
    event RefundIssued(uint256 indexed jobId, address indexed client, uint256 amount);

    modifier jobExists(uint256 _jobId) {
        require(jobs[_jobId].client != address(0), "Job does not exist");
        _;
    }

    modifier onlyOracle() {
        require(msg.sender == scoreOracle, "Only the score oracle can report scores");
        _;
    }

    constructor(address _scoreOracle, address _reputationContract) {
        scoreOracle = _scoreOracle;
        reputationContract = IReputationNFT(_reputationContract);
    }

    /**
     * Client posts a job, deposits payment, and sets the minimum
     * compliance score (threshold) required for automatic release --
     * agreed between client and freelancer before work begins.
     */
    function createJob(uint256 _jobId, string memory _jobTitle, uint256 _threshold) public payable {
        require(msg.value > 0, "Payment required");
        require(jobs[_jobId].client == address(0), "Job already exists");
        require(_threshold <= 100, "Threshold must be 0-100");
jobs[_jobId] = Job({
    jobId: _jobId,
    client: payable(msg.sender),
    freelancer: payable(address(0)),
    amount: msg.value,
    threshold: _threshold,
    jobTitle: _jobTitle,
    ipfsCID: "",
    submissionType: "",
    aiScore: 0,
    status: JobStatus.Open
});

        emit JobCreated(_jobId, msg.sender, msg.value, _threshold);
    }

    function assignFreelancer(uint256 _jobId, address payable _freelancer) public jobExists(_jobId) {
        Job storage job = jobs[_jobId];
        require(msg.sender == job.client, "Only client can assign freelancer");
        require(job.status == JobStatus.Open, "Job is not open");

        job.freelancer = _freelancer;
        job.status = JobStatus.Assigned;

        emit FreelancerAssigned(_jobId, _freelancer);
    }

    /**
     * Freelancer submits their work's IPFS CID only -- notice this
     * NO LONGER accepts an aiScore parameter. The score comes later,
     * separately, only from the trusted oracle (see recordScore below).
     */
    function submitWork(
    uint256 _jobId,
    string memory _ipfsCID,
    string memory _submissionType
) public jobExists(_jobId) {
    Job storage job = jobs[_jobId];

    require(
        msg.sender == job.freelancer,
        "Only assigned freelancer can submit"
    );

    require(
        job.status == JobStatus.Assigned,
        "Job not assigned"
    );

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

   emit WorkSubmitted(
    _jobId,
    _ipfsCID,
    _submissionType
);
}
    /**
     * THE CORE FIX: called by your Python/web3.py bridge (the oracle)
     * after the AI compliance score has been calculated off-chain.
     * This function does everything in ONE transaction:
     *   1. Records the trusted score.
     *   2. Immediately checks it against the threshold.
     *   3. If it clears -> releases payment AND mints the reputation
     *      NFT automatically, no further human action needed.
     *   4. If it doesn't clear -> holds funds for manual dispute review.
     */
    function recordScore(uint256 _jobId, uint256 _aiScore) public jobExists(_jobId) onlyOracle {
        Job storage job = jobs[_jobId];
        require(job.status == JobStatus.Submitted, "Work not yet submitted");
        require(_aiScore <= 100, "Score must be 0-100");

        job.aiScore = _aiScore;
        emit ScoreRecorded(_jobId, _aiScore);

        if (_aiScore >= job.threshold) {
            job.status = JobStatus.Released;

            (bool success, ) = job.freelancer.call{value: job.amount}("");
            require(success, "Payment transfer failed");
            emit PaymentReleased(_jobId, job.freelancer, job.amount);

            // FIX 3: reputation updates automatically, same transaction
            reputationContract.mintReputation(job.freelancer, _aiScore);
        } else {
            job.status = JobStatus.Held;
            emit PaymentHeld(_jobId, _aiScore, job.threshold);
        }
    }

    /**
     * Dispute path: if a job was held, the client can still manually
     * release payment after reviewing the AI report themselves. This
     * is the ONLY case a human is involved -- the exception path, not
     * the normal path (which is now fully automatic via recordScore).
     */
    function manualRelease(uint256 _jobId) public jobExists(_jobId) {
        Job storage job = jobs[_jobId];
        require(msg.sender == job.client, "Only client can manually release");
        require(job.status == JobStatus.Held, "Job is not in held state");

        job.status = JobStatus.Released;

        (bool success, ) = job.freelancer.call{value: job.amount}("");
        require(success, "Payment transfer failed");
        emit PaymentReleased(_jobId, job.freelancer, job.amount);

        reputationContract.mintReputation(job.freelancer, job.aiScore);
    }

    function refundClient(uint256 _jobId) public jobExists(_jobId) {
        Job storage job = jobs[_jobId];
        require(msg.sender == job.client, "Only client can refund");
        require(job.status != JobStatus.Released, "Payment already released");

        job.status = JobStatus.Refunded;

        (bool success, ) = job.client.call{value: job.amount}("");
        require(success, "Refund transfer failed");
        emit RefundIssued(_jobId, job.client, job.amount);
    }

    function getJob(uint256 _jobId) public view returns (Job memory) {
        return jobs[_jobId];
    }
}
