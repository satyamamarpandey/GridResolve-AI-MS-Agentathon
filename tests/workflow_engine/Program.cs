// Runs a GridResolveAIWorkflow YAML definition through Microsoft's open-source
// declarative workflow engine (NuGet: Microsoft.Agents.AI.Workflows.Declarative),
// with every agent replaced by a scripted reply. No network, no model, no cost.
//
//   dotnet run --project tests/workflow_engine -- <workflow.yaml> <scenario.json>
//
// scenario.json: { "input": "<first user message>",
//                  "agents": { "<AgentName>": "<the text that agent replies with>" } }
//
// Prints one line per observed fact, then a JSON summary on the last line:
//   EXECUTED <action id>      an action completed
//   INVOKED  <agent name>     the engine asked the provider to run that agent
//   SENT     <text>           a SendActivity message, exactly as delivered
//   FAILED   <id>: <message>  an action failed
//
// What this establishes: how Microsoft's open-source engine runs this YAML.
// What it does not: that the closed-source hosted Foundry service behaves the
// same. It is calibrated against the one real run: see tests/test_workflow_engine.py.
using System.Runtime.CompilerServices;
using System.Text.Json;
using Microsoft.Agents.AI;
using Microsoft.Agents.AI.Workflows;
using Microsoft.Agents.AI.Workflows.Declarative;
using Microsoft.Agents.AI.Workflows.Declarative.Events;
using Microsoft.Extensions.AI;

if (args.Length != 2)
{
    Console.Error.WriteLine("usage: workflow_engine <workflow.yaml> <scenario.json>");
    return 2;
}

using JsonDocument scenario = JsonDocument.Parse(File.ReadAllText(args[1]));
string input = scenario.RootElement.GetProperty("input").GetString() ?? string.Empty;
Dictionary<string, string> replies = scenario.RootElement.GetProperty("agents")
    .EnumerateObject().ToDictionary(p => p.Name, p => p.Value.GetString() ?? string.Empty);

ScriptedProvider provider = new(replies);
List<string> executed = [], sent = [], failed = [];
try
{
    using StreamReader yaml = File.OpenText(args[0]);
    Workflow workflow = DeclarativeWorkflowBuilder.Build<string>(yaml, new DeclarativeWorkflowOptions(provider));
    await using StreamingRun run = await InProcessExecution.RunStreamingAsync(workflow, input);
    await foreach (WorkflowEvent evt in run.WatchStreamAsync())
    {
        switch (evt)
        {
            case ExecutorCompletedEvent done:
                executed.Add(done.ExecutorId);
                Console.WriteLine("EXECUTED " + done.ExecutorId);
                break;
            case MessageActivityEvent message:
                sent.Add(message.Message);
                Console.WriteLine("SENT     " + message.Message.Replace("\n", "\\n"));
                break;
            case ExecutorFailedEvent failure:
                failed.Add(failure.ExecutorId + ": " + failure.Data?.Message);
                Console.WriteLine("FAILED   " + failed[^1]);
                break;
            case WorkflowErrorEvent error:
                failed.Add("workflow: " + (error.Data as Exception)?.Message);
                Console.WriteLine("FAILED   " + failed[^1]);
                break;
        }
    }
}
catch (Exception ex)
{
    failed.Add("build-or-run: " + ex.GetType().Name + ": " + ex.Message);
    Console.WriteLine("FAILED   " + failed[^1]);
}

foreach (string name in provider.Invoked) Console.WriteLine("INVOKED  " + name);
// inputs: for each invocation, the messages the workflow node passed in, and the role of
// the last turn the agent would see on the shared conversation once those are appended.
Console.WriteLine(JsonSerializer.Serialize(new { executed, invoked = provider.Invoked, sent, failed, inputs = provider.Inputs }));
return 0;

internal sealed class ScriptedProvider(Dictionary<string, string> replies) : ResponseAgentProvider
{
    private readonly Dictionary<string, List<ChatMessage>> _conversations = [];
    public List<string> Invoked { get; } = [];
    public List<InvocationInput> Inputs { get; } = [];

    public override Task<string> CreateConversationAsync(CancellationToken cancellationToken = default)
    {
        string id = "conv_" + Guid.NewGuid().ToString("N");
        _conversations[id] = [];
        return Task.FromResult(id);
    }

    public override Task<ChatMessage> CreateMessageAsync(string conversationId, ChatMessage conversationMessage, CancellationToken cancellationToken = default)
    {
        conversationMessage.MessageId ??= "msg_" + Guid.NewGuid().ToString("N");
        Messages(conversationId).Add(conversationMessage);
        return Task.FromResult(conversationMessage);
    }

    public override Task<ChatMessage> GetMessageAsync(string conversationId, string messageId, CancellationToken cancellationToken = default) =>
        Task.FromResult(Messages(conversationId).First(m => m.MessageId == messageId));

    public override async IAsyncEnumerable<AgentResponseUpdate> InvokeAgentAsync(
        string agentId, string? agentVersion, string? conversationId, IEnumerable<ChatMessage>? messages,
        IDictionary<string, object?>? inputArguments, [EnumeratorCancellation] CancellationToken cancellationToken = default)
    {
        await Task.CompletedTask;
        Invoked.Add(agentId);
        // The hosted service appends a node's input messages to the shared conversation before
        // the agent runs, so the agent's last visible turn is the node's own message when one
        // is given, and the previous agent's assistant turn when none is.
        List<ChatMessage> given = (messages ?? []).Where(m => !string.IsNullOrEmpty(m.Text)).ToList();
        if (conversationId is not null) Messages(conversationId).AddRange(given);
        List<ChatMessage> visible = conversationId is null ? given : Messages(conversationId);
        Inputs.Add(new InvocationInput(agentId,
            given.Select(m => new GivenMessage(m.Role.Value, m.Text)).ToList(),
            visible.Count == 0 ? "none" : visible[^1].Role.Value));
        if (!replies.TryGetValue(agentId, out string? text))
        {
            throw new InvalidOperationException("The scenario scripts no reply for agent " + agentId);
        }
        string messageId = "msg_" + Guid.NewGuid().ToString("N");
        if (conversationId is not null)
        {
            Messages(conversationId).Add(new ChatMessage(ChatRole.Assistant, text) { MessageId = messageId, AuthorName = agentId });
        }
        yield return new AgentResponseUpdate(ChatRole.Assistant, [new TextContent(text)])
        {
            MessageId = messageId, ResponseId = "resp_" + agentId, AuthorName = agentId,
        };
    }

    public override async IAsyncEnumerable<ChatMessage> GetMessagesAsync(
        string conversationId, int? limit = null, string? after = null, string? before = null,
        bool newestFirst = false, [EnumeratorCancellation] CancellationToken cancellationToken = default)
    {
        await Task.CompletedTask;
        IEnumerable<ChatMessage> all = Messages(conversationId);
        foreach (ChatMessage message in newestFirst ? all.Reverse() : all) yield return message;
    }

    private List<ChatMessage> Messages(string conversationId) =>
        _conversations.TryGetValue(conversationId, out List<ChatMessage>? list) ? list : _conversations[conversationId] = [];
}

internal sealed record GivenMessage(string Role, string Text);

internal sealed record InvocationInput(string Agent, List<GivenMessage> Given, string LastVisibleRole);
