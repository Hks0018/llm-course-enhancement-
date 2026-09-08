# Practical Cloud Deployment

A short course on deploying applications to the cloud, written to exercise every branch of the Universal Course Enhancement Engine's decision logic.

Learning Objectives:
- Explain what cloud deployment means and why teams use it
- Choose a deployment strategy based on real constraints
- Compare cloud and on-premise hosting on cost, control, and speed
- Describe how a request flows through a typical deployed system

## Module 1: Getting Started

### What Is Cloud Deployment?

Cloud deployment means running your application on infrastructure owned and operated by a third-party provider instead of your own hardware. Teams do this to move faster and avoid managing physical servers.

### Setting Up Your Deployment Pipeline

Before you can deploy anything, you need a working pipeline. Follow these steps in order.

1. Create an account with your chosen cloud provider.
2. Install the provider's command-line tool on your machine.
3. Authenticate the command-line tool with your account credentials.
4. Write a small configuration file describing your application.
5. Run the deploy command and watch the build logs for errors.
6. Verify the deployed application responds correctly at its public URL.

First, get the account set up. Then install the tooling. After that, authenticate and configure. Finally, deploy and verify - in that exact order, or later steps will fail with confusing errors.

## Module 2: Choosing an Approach

### Picking a Deployment Strategy

Your choice of deployment strategy depends heavily on your team's constraints, and the wrong choice compounds over time.

If your team is small and has no dedicated infrastructure staff, a fully managed platform is usually the right call, since it trades some control for dramatically less operational burden.

If your application has strict data-residency or compliance requirements, a self-managed cloud deployment gives you the control you need, even though it takes more engineering time to operate.

When your traffic is highly unpredictable and spiky, a serverless deployment style handles the scaling automatically, whereas a fixed-size deployment would require manual capacity planning.

Unless you have a specific reason to avoid it, most new teams should default to the fully managed option and revisit the decision only once a concrete constraint forces the issue.

### Cloud vs On-Premise Hosting

Cloud hosting and on-premise hosting solve the same underlying problem - giving your application somewhere to run - but they make very different trade-offs.

Cloud is generally faster to get started with compared to on-premise, since there is no hardware to purchase or rack before you can deploy. On-premise, in contrast, requires significant upfront capital investment before a single request can be served.

On the other hand, on-premise hosting gives you full physical control over your hardware and data, whereas cloud hosting means trusting a third party with both. Cost also behaves differently: cloud is typically pay-as-you-go, which is cheaper at small scale but can become more expensive than on-premise at very large, steady scale.

### A Brief History of Cloud Computing

Cloud computing did not appear overnight. In 1999, Salesforce popularized the idea of delivering enterprise software entirely over the web rather than as installed software. In 2002, Amazon began experimenting internally with web-based infrastructure services. In 2006, Amazon Web Services launched EC2 and S3 to the public, which is widely considered the start of the modern cloud era. In 2008, Google App Engine and Microsoft's early Azure offerings brought major competitors into the market. By 2010, cloud adoption had moved from early-adopter startups into mainstream enterprise IT.

## Module 3: How Deployed Systems Work

### Request Flow In a Deployed System

Understanding what actually happens when a user hits your deployed application is one of the more conceptually dense topics in this course, and it rewards careful attention because the same pattern recurs in almost every architecture you will encounter professionally, whether you are running a small side project or a large-scale production service handling millions of concurrent users across multiple geographic regions.

When a client sends a request, it first reaches a load balancer, which distributes incoming traffic across multiple identical copies of your application server. The server that receives the request typically calls one or more backend services - for example, it might query a database, or it might call an external API for data it does not own. Once the server has everything it needs, it constructs a response and returns it to the load balancer, which forwards it back to the original client. If the database is slow or unavailable, the server may instead return a cached response while it retries the request in the background, which keeps the system responsive even under partial failure.

This request/response cycle, multiplied across every concurrent user, is what a deployed system's infrastructure exists to support reliably.

### Deployment Terminology You Should Know

This lesson defines the core vocabulary used throughout the rest of the course.

A deployment pipeline is defined as the automated sequence of steps that takes source code from a repository to a running application. A load balancer refers to a component that distributes incoming network traffic across multiple servers so that no single server is overwhelmed. Horizontal scaling is defined as adding more machines to handle increased load, as opposed to making a single machine more powerful. A rollback refers to the act of reverting a deployment to its previous known-good version after a failed release.

Knowing these terms precisely matters, because deployment documentation and tooling use them constantly, and imprecise understanding of them is one of the most common sources of confusion for engineers new to cloud deployment.
