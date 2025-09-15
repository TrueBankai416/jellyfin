using MediaBrowser.Controller;
using MediaBrowser.Controller.Plugins;
using Microsoft.Extensions.DependencyInjection;
using Jellyfin.Plugin.MissingEpisodeAlert.Services;

namespace Jellyfin.Plugin.MissingEpisodeAlert;

/// <summary>
/// Plugin service registrator for dependency injection.
/// </summary>
public class PluginServiceRegistrator : IPluginServiceRegistrator
{
    /// <inheritdoc />
    public void RegisterServices(IServiceCollection serviceCollection, IServerApplicationHost applicationHost)
    {
        serviceCollection.AddSingleton<MissingEpisodeDetectionService>();
        serviceCollection.AddSingleton<NotificationService>();
        serviceCollection.AddSingleton<PlaybackMonitorService>();
        
        // Force instantiation of PlaybackMonitorService to ensure event subscription
        serviceCollection.AddSingleton<IPluginInitializer>(provider => 
            new PluginInitializer(provider.GetRequiredService<PlaybackMonitorService>()));
    }
}

/// <summary>
/// Interface for plugin initialization.
/// </summary>
public interface IPluginInitializer
{
    /// <summary>
    /// Gets a value indicating whether the plugin is initialized.
    /// </summary>
    bool IsInitialized { get; }
}

/// <summary>
/// Plugin initializer that ensures services are instantiated.
/// </summary>
public class PluginInitializer : IPluginInitializer
{
    /// <summary>
    /// Initializes a new instance of the <see cref="PluginInitializer"/> class.
    /// </summary>
    /// <param name="playbackMonitorService">The playback monitor service to initialize.</param>
    public PluginInitializer(PlaybackMonitorService playbackMonitorService)
    {
        // The service is instantiated by DI, which triggers its constructor and event subscription
        IsInitialized = playbackMonitorService != null;
    }

    /// <inheritdoc />
    public bool IsInitialized { get; }
}
