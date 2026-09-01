const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("FreelanceEscrow", function () {
  let escrow;
  let nft;
  let client;
  let freelancer;
  let other;
  let oracle;

  const JOB_ID = 1;
  const PAYMENT = ethers.parseEther("1");
  const THRESHOLD = 70;

  beforeEach(async function () {
    [client, freelancer, other, oracle] = await ethers.getSigners();

    // Deploy ReputationNFT
    const ReputationNFT = await ethers.getContractFactory("ReputationNFT");
    nft = await ReputationNFT.deploy(client.address);
    await nft.waitForDeployment();

    // Deploy Escrow
    const FreelanceEscrow =
      await ethers.getContractFactory("FreelanceEscrow");

    escrow = await FreelanceEscrow.deploy(
  oracle.address,
  await nft.getAddress()
);

    await escrow.waitForDeployment();

    // Transfer NFT ownership to escrow
    await nft.transferOwnership(await escrow.getAddress());
  });

  it("1. should create a job", async function () {
    await escrow
      .connect(client)
      .createJob(JOB_ID, "Test Job", THRESHOLD, {
        value: PAYMENT,
      });

    const job = await escrow.getJob(JOB_ID);

    expect(job.client).to.equal(client.address);
    expect(job.amount).to.equal(PAYMENT);
    expect(job.threshold).to.equal(THRESHOLD);
  });

  it("2. should assign freelancer", async function () {
    await escrow
      .connect(client)
      .createJob(JOB_ID, "Test Job", THRESHOLD, {
        value: PAYMENT,
      });

    await escrow
      .connect(client)
      .assignFreelancer(JOB_ID, freelancer.address);

    const job = await escrow.getJob(JOB_ID);

    expect(job.freelancer).to.equal(freelancer.address);
  });

  it("3. freelancer should submit work", async function () {
    await escrow
      .connect(client)
      .createJob(JOB_ID, "Test Job", THRESHOLD, {
        value: PAYMENT,
      });

    await escrow
      .connect(client)
      .assignFreelancer(JOB_ID, freelancer.address);

    await escrow
      .connect(freelancer)
      .submitWork(JOB_ID, "QmTestCID");

    const job = await escrow.getJob(JOB_ID);

    expect(job.ipfsCID).to.equal("QmTestCID");
    expect(job.status).to.equal(2);
  });

  it("4. non-oracle should NOT record score", async function () {
    await escrow
      .connect(client)
      .createJob(JOB_ID, "Test Job", THRESHOLD, {
        value: PAYMENT,
      });

    await escrow
      .connect(client)
      .assignFreelancer(JOB_ID, freelancer.address);

    await escrow
      .connect(freelancer)
      .submitWork(JOB_ID, "QmTestCID");

    await expect(
      escrow
        .connect(other)
        .recordScore(JOB_ID, 90)
    ).to.be.reverted;
  });

  it("5. score >= threshold should release payment and mint NFT", async function () {
    await escrow
      .connect(client)
      .createJob(JOB_ID, "Test Job", THRESHOLD, {
        value: PAYMENT,
      });

    await escrow
      .connect(client)
      .assignFreelancer(JOB_ID, freelancer.address);

    await escrow
      .connect(freelancer)
      .submitWork(JOB_ID, "QmTestCID");

    const balanceBefore = await ethers.provider.getBalance(
      freelancer.address
    );

    const tx = await escrow
      .connect(oracle)
      .recordScore(JOB_ID, 90);

    const receipt = await tx.wait();

    const balanceAfter = await ethers.provider.getBalance(
      freelancer.address
    );

    const job = await escrow.getJob(JOB_ID);

    expect(job.status).to.equal(3);
    expect(job.aiScore).to.equal(90);
    expect(balanceAfter).to.be.greaterThan(balanceBefore);

    expect(await nft.ownerOf(0)).to.equal(freelancer.address);
  });

  it("6. score below threshold should HOLD payment", async function () {
    await escrow
      .connect(client)
      .createJob(JOB_ID, "Test Job", THRESHOLD, {
        value: PAYMENT,
      });

    await escrow
      .connect(client)
      .assignFreelancer(JOB_ID, freelancer.address);

    await escrow
      .connect(freelancer)
      .submitWork(JOB_ID, "QmTestCID");

    await escrow
      .connect(oracle)
      .recordScore(JOB_ID, 40);

    const job = await escrow.getJob(JOB_ID);

    expect(job.status).to.equal(4);
    expect(job.aiScore).to.equal(40);
  });
});
